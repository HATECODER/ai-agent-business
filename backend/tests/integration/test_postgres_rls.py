import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
from uuid import UUID

from alembic import command
from alembic.config import Config
import psycopg
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from backend.app.authorization import AuthorizationDenied, MerchantRole, TenantAuthority
from backend.app.database import tenant_transaction
from backend.app.identity import VerifiedIdentity
from backend.app.memberships import persistent_authority_resolver


BACKEND_ROOT = Path(__file__).resolve().parents[2]
DATABASE_URL = os.getenv("BIZPILOT_TEST_DATABASE_URL", "").strip()
PSYCOPG_URL = DATABASE_URL.replace("postgresql+psycopg://", "postgresql://", 1)

TENANT_A = UUID("10000000-0000-0000-0000-000000000001")
TENANT_B = UUID("20000000-0000-0000-0000-000000000001")
IDENTITY_A = UUID("10000000-0000-0000-0000-000000000002")
IDENTITY_B = UUID("20000000-0000-0000-0000-000000000002")
MEMBERSHIP_A = UUID("10000000-0000-0000-0000-000000000003")
MEMBERSHIP_B = UUID("20000000-0000-0000-0000-000000000003")
LOCATION_A = UUID("10000000-0000-0000-0000-000000000004")
LOCATION_B = UUID("20000000-0000-0000-0000-000000000004")


pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="BIZPILOT_TEST_DATABASE_URL is required for PostgreSQL integration tests",
)


def authority_a(permission_version=1):
    return TenantAuthority(
        identity_id=str(IDENTITY_A),
        membership_id=str(MEMBERSHIP_A),
        tenant_id=str(TENANT_A),
        role=MerchantRole.OWNER,
        permission_version=permission_version,
    )


@pytest.fixture(scope="module")
def migrated_database():
    roles_sql = (BACKEND_ROOT / "sql" / "roles.sql").read_text(encoding="utf-8")
    with psycopg.connect(PSYCOPG_URL, autocommit=True) as connection:
        connection.execute(roles_sql)

    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", DATABASE_URL.replace("%", "%%"))
    command.upgrade(config, "head")
    engine = create_engine(DATABASE_URL)
    with engine.begin() as connection:
        connection.execute(text("""
            INSERT INTO tenants (id, slug, display_name)
            VALUES (:tenant_a, 'tenant-a', 'Tenant A'), (:tenant_b, 'tenant-b', 'Tenant B')
        """), {"tenant_a": TENANT_A, "tenant_b": TENANT_B})
        connection.execute(text("""
            INSERT INTO identities (id, issuer, subject, display_name)
            VALUES
                (:identity_a, 'https://identity.example', 'user-a', 'User A'),
                (:identity_b, 'https://identity.example', 'user-b', 'User B')
        """), {"identity_a": IDENTITY_A, "identity_b": IDENTITY_B})
        connection.execute(text("""
            INSERT INTO memberships (id, tenant_id, identity_id, role)
            VALUES
                (:membership_a, :tenant_a, :identity_a, 'owner'),
                (:membership_b, :tenant_b, :identity_b, 'owner')
        """), {
            "membership_a": MEMBERSHIP_A,
            "tenant_a": TENANT_A,
            "identity_a": IDENTITY_A,
            "membership_b": MEMBERSHIP_B,
            "tenant_b": TENANT_B,
            "identity_b": IDENTITY_B,
        })
        connection.execute(text("""
            INSERT INTO locations (id, tenant_id, code, name)
            VALUES
                (:location_a, :tenant_a, 'DHAKA-A', 'Tenant A Warehouse'),
                (:location_b, :tenant_b, 'DHAKA-B', 'Tenant B Warehouse')
        """), {
            "location_a": LOCATION_A,
            "tenant_a": TENANT_A,
            "location_b": LOCATION_B,
            "tenant_b": TENANT_B,
        })
    try:
        yield engine
    finally:
        engine.dispose()
        command.downgrade(config, "base")


@pytest.fixture(autouse=True)
def reset_tenant_a_membership(migrated_database):
    with migrated_database.begin() as connection:
        connection.execute(text("""
            UPDATE memberships
            SET status = 'active', permission_version = 1
            WHERE id = :id
        """), {"id": MEMBERSHIP_A})
        connection.execute(text("""
            UPDATE identities
            SET status = 'active', tokens_valid_after = NULL
            WHERE id = :id
        """), {"id": IDENTITY_A})


def test_runtime_sees_only_active_tenant_rows(migrated_database):
    with tenant_transaction(migrated_database, authority_a()) as connection:
        rows = connection.execute(text("SELECT id, name FROM locations ORDER BY name")).mappings().all()
    assert [dict(row) for row in rows] == [{"id": LOCATION_A, "name": "Tenant A Warehouse"}]


def test_runtime_role_is_restricted_and_does_not_own_tables(migrated_database):
    with migrated_database.connect() as connection:
        roles = connection.execute(text("""
            SELECT rolname, rolsuper, rolcreatedb, rolcreaterole, rolbypassrls
            FROM pg_roles
            WHERE rolname IN ('bizpilot_runtime', 'bizpilot_authenticator')
            ORDER BY rolname
        """)).mappings().all()
        table_owner = connection.execute(text("""
            SELECT tableowner FROM pg_tables
            WHERE schemaname = 'public' AND tablename = 'locations'
        """)).scalar_one()
        forced_tables = set(connection.execute(text("""
            SELECT relname FROM pg_class
            WHERE relname IN ('locations', 'audit_events') AND relforcerowsecurity
        """)).scalars())
        auth_can_select_identity = connection.execute(text(
            "SELECT has_table_privilege('bizpilot_authenticator', 'identities', 'SELECT')"
        )).scalar_one()
        auth_can_resolve = connection.execute(text("""
            SELECT has_function_privilege(
                'bizpilot_authenticator',
                'bizpilot_resolve_membership(text,text,uuid,timestamptz)',
                'EXECUTE'
            )
        """)).scalar_one()
        runtime_can_resolve = connection.execute(text("""
            SELECT has_function_privilege(
                'bizpilot_runtime',
                'bizpilot_resolve_membership(text,text,uuid,timestamptz)',
                'EXECUTE'
            )
        """)).scalar_one()
    assert [dict(role) for role in roles] == [
        {
            "rolname": role_name,
            "rolsuper": False,
            "rolcreatedb": False,
            "rolcreaterole": False,
            "rolbypassrls": False,
        }
        for role_name in ("bizpilot_authenticator", "bizpilot_runtime")
    ]
    assert table_owner != "bizpilot_runtime"
    assert forced_tables == {"locations", "audit_events"}
    assert auth_can_select_identity is False
    assert auth_can_resolve is True
    assert runtime_can_resolve is False


def test_runtime_cannot_read_or_insert_cross_tenant_rows(migrated_database):
    with tenant_transaction(migrated_database, authority_a()) as connection:
        row = connection.execute(
            text("SELECT name FROM locations WHERE id = :id"), {"id": LOCATION_B}
        ).first()
    assert row is None

    with pytest.raises(DBAPIError):
        with tenant_transaction(migrated_database, authority_a()) as connection:
            connection.execute(text("""
                INSERT INTO locations (id, tenant_id, code, name)
                VALUES (:id, :tenant_id, 'FORGED', 'Forged location')
            """), {"id": UUID("30000000-0000-0000-0000-000000000001"), "tenant_id": TENANT_B})


def test_runtime_cannot_read_platform_staff(migrated_database):
    with pytest.raises(DBAPIError):
        with tenant_transaction(migrated_database, authority_a()) as connection:
            connection.execute(text("SELECT identity_id FROM platform_staff")).all()


def test_revocation_and_permission_version_take_effect(migrated_database):
    with migrated_database.begin() as connection:
        connection.execute(
            text("UPDATE memberships SET permission_version = 2 WHERE id = :id"),
            {"id": MEMBERSHIP_A},
        )
    with tenant_transaction(migrated_database, authority_a(permission_version=1)) as connection:
        assert connection.execute(text("SELECT id FROM locations")).all() == []
    with tenant_transaction(migrated_database, authority_a(permission_version=2)) as connection:
        assert connection.execute(text("SELECT id FROM locations")).scalars().all() == [LOCATION_A]

    with migrated_database.begin() as connection:
        connection.execute(
            text("UPDATE memberships SET status = 'revoked' WHERE id = :id"),
            {"id": MEMBERSHIP_A},
        )
    with tenant_transaction(migrated_database, authority_a(permission_version=2)) as connection:
        assert connection.execute(text("SELECT id FROM locations")).all() == []


def test_persistent_auth_lookup_rechecks_tenant_membership_and_session_cutoff(
    migrated_database,
):
    issued_at = datetime.now(timezone.utc).replace(microsecond=0)
    identity = VerifiedIdentity(
        "https://identity.example",
        "user-a",
        issued_at,
        issued_at + timedelta(minutes=10),
    )
    resolve = persistent_authority_resolver(migrated_database)
    authority = resolve(identity, str(TENANT_A))
    assert authority == authority_a()

    with pytest.raises(AuthorizationDenied):
        resolve(identity, str(TENANT_B))

    with migrated_database.begin() as connection:
        connection.execute(text("""
            UPDATE identities
            SET tokens_valid_after = :cutoff
            WHERE id = :id
        """), {"cutoff": issued_at + timedelta(seconds=1), "id": IDENTITY_A})
    with pytest.raises(AuthorizationDenied):
        resolve(identity, str(TENANT_A))

    with migrated_database.begin() as connection:
        connection.execute(text("""
            UPDATE identities
            SET status = 'revoked', tokens_valid_after = NULL
            WHERE id = :identity_id
        """), {"identity_id": IDENTITY_A})
    with pytest.raises(AuthorizationDenied):
        resolve(identity, str(TENANT_A))

    with migrated_database.begin() as connection:
        connection.execute(text("""
            UPDATE identities SET status = 'active' WHERE id = :identity_id
        """), {"identity_id": IDENTITY_A})
        connection.execute(text("""
            UPDATE memberships
            SET status = 'revoked'
            WHERE id = :membership_id
        """), {"membership_id": MEMBERSHIP_A})
    with pytest.raises(AuthorizationDenied):
        resolve(identity, str(TENANT_A))

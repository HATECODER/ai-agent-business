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
from backend.app.inventory import database_inventory_reader
from backend.app.inventory_import import (
    ImportRejected,
    database_error_reporter,
    database_import_previewer,
)
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
PRODUCT_A = UUID("10000000-0000-0000-0000-000000000005")
PRODUCT_B = UUID("20000000-0000-0000-0000-000000000005")
VARIANT_A = UUID("10000000-0000-0000-0000-000000000006")
VARIANT_B = UUID("20000000-0000-0000-0000-000000000006")
BALANCE_A = UUID("10000000-0000-0000-0000-000000000007")
BALANCE_B = UUID("20000000-0000-0000-0000-000000000007")
VARIANT_A_2 = UUID("10000000-0000-0000-0000-000000000008")
BALANCE_A_2 = UUID("10000000-0000-0000-0000-000000000009")


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


def authority_b():
    return TenantAuthority(
        identity_id=str(IDENTITY_B),
        membership_id=str(MEMBERSHIP_B),
        tenant_id=str(TENANT_B),
        role=MerchantRole.OWNER,
        permission_version=1,
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
        connection.execute(text("""
            INSERT INTO products
                (id, tenant_id, name, source_kind, source_reference, source_version, observed_at)
            VALUES
                (:product_a, :tenant_a, 'Tenant A Shirt', 'csv_snapshot', 'import-a', 'v1', CURRENT_TIMESTAMP),
                (:product_b, :tenant_b, 'Tenant B Shoe', 'csv_snapshot', 'import-b', 'v1', CURRENT_TIMESTAMP)
        """), {
            "product_a": PRODUCT_A,
            "tenant_a": TENANT_A,
            "product_b": PRODUCT_B,
            "tenant_b": TENANT_B,
        })
        connection.execute(text("""
            INSERT INTO product_variants
                (id, tenant_id, product_id, sku, name, base_price_minor, currency,
                 source_kind, source_reference, source_version, observed_at)
            VALUES
                (:variant_a, :tenant_a, :product_a, 'A-SHIRT-M', 'Medium', 125000, 'BDT',
                 'csv_snapshot', 'import-a', 'v1', CURRENT_TIMESTAMP),
                (:variant_a_2, :tenant_a, :product_a, 'A-SHIRT-L', 'Large', 125000, 'BDT',
                 'csv_snapshot', 'import-a', 'v1', CURRENT_TIMESTAMP),
                (:variant_b, :tenant_b, :product_b, 'B-SHOE-42', 'Size 42', 320000, 'BDT',
                 'csv_snapshot', 'import-b', 'v1', CURRENT_TIMESTAMP)
        """), {
            "variant_a": VARIANT_A,
            "variant_a_2": VARIANT_A_2,
            "tenant_a": TENANT_A,
            "product_a": PRODUCT_A,
            "variant_b": VARIANT_B,
            "tenant_b": TENANT_B,
            "product_b": PRODUCT_B,
        })
        connection.execute(text("""
            INSERT INTO inventory_balances
                (id, tenant_id, variant_id, location_id, quantity, low_stock_threshold,
                 source_kind, source_reference, source_version, observed_at)
            VALUES
                (:balance_a, :tenant_a, :variant_a, :location_a, 3, 5,
                 'csv_snapshot', 'import-a', 'v1', CURRENT_TIMESTAMP),
                (:balance_a_2, :tenant_a, :variant_a_2, :location_a, 10, 2,
                 'csv_snapshot', 'import-a', 'v1', CURRENT_TIMESTAMP),
                (:balance_b, :tenant_b, :variant_b, :location_b, 20, 4,
                 'csv_snapshot', 'import-b', 'v1', CURRENT_TIMESTAMP)
        """), {
            "balance_a": BALANCE_A,
            "balance_a_2": BALANCE_A_2,
            "tenant_a": TENANT_A,
            "variant_a": VARIANT_A,
            "variant_a_2": VARIANT_A_2,
            "location_a": LOCATION_A,
            "balance_b": BALANCE_B,
            "tenant_b": TENANT_B,
            "variant_b": VARIANT_B,
            "location_b": LOCATION_B,
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


def test_inventory_reader_returns_only_current_tenant_with_source_evidence(
    migrated_database,
):
    page = database_inventory_reader(migrated_database)(authority_a(), 50, None, False)
    assert len(page.items) == 2
    item = page.items[0]
    assert item.inventory_id == BALANCE_A
    assert item.product_name == "Tenant A Shirt"
    assert item.sku == "A-SHIRT-M"
    assert item.quantity == 3
    assert item.low_stock_threshold == 5
    assert item.is_low_stock is True
    assert item.base_price_minor == 125000
    assert item.currency == "BDT"
    assert item.source_kind == "csv_snapshot"
    assert item.source_version == "v1"
    assert page.next_cursor is None

    first_page = database_inventory_reader(migrated_database)(authority_a(), 1, None, False)
    assert [entry.inventory_id for entry in first_page.items] == [BALANCE_A]
    assert first_page.next_cursor == BALANCE_A
    second_page = database_inventory_reader(migrated_database)(
        authority_a(), 1, first_page.next_cursor, False
    )
    assert [entry.inventory_id for entry in second_page.items] == [BALANCE_A_2]
    assert second_page.next_cursor is None

    low_stock = database_inventory_reader(migrated_database)(authority_a(), 1, None, True)
    assert [entry.inventory_id for entry in low_stock.items] == [BALANCE_A]


def test_runtime_inventory_is_read_only_and_cross_tenant_rows_are_hidden(
    migrated_database,
):
    with tenant_transaction(migrated_database, authority_a()) as connection:
        assert connection.execute(
            text("SELECT id FROM products WHERE id = :id"), {"id": PRODUCT_B}
        ).first() is None
        counts = {
            table: connection.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
            for table in (
                "products",
                "product_variants",
                "inventory_balances",
                "inventory_movements",
            )
        }
    assert counts == {
        "products": 1,
        "product_variants": 2,
        "inventory_balances": 2,
        "inventory_movements": 0,
    }

    with pytest.raises(DBAPIError):
        with tenant_transaction(migrated_database, authority_a()) as connection:
            connection.execute(text("""
                INSERT INTO products
                    (id, tenant_id, name, source_kind, observed_at)
                VALUES
                    (:id, :tenant_id, 'Unauthorized write', 'manual', CURRENT_TIMESTAMP)
            """), {
                "id": UUID("30000000-0000-0000-0000-000000000005"),
                "tenant_id": TENANT_A,
            })

    with pytest.raises(DBAPIError):
        with tenant_transaction(migrated_database, authority_a()) as connection:
            connection.execute(text("""
                INSERT INTO locations (id, tenant_id, code, name)
                VALUES (:id, :tenant_id, 'NO-WRITE', 'Unauthorized location')
            """), {
                "id": UUID("30000000-0000-0000-0000-000000000006"),
                "tenant_id": TENANT_A,
            })


def test_inventory_composite_keys_reject_cross_tenant_relationships(
    migrated_database,
):
    with pytest.raises(DBAPIError):
        with migrated_database.begin() as connection:
            connection.execute(text("""
                INSERT INTO product_variants
                    (id, tenant_id, product_id, sku, name, source_kind,
                     source_reference, observed_at)
                VALUES
                    (:id, :tenant_b, :product_a, 'FORGED-SKU', 'Forged',
                     'csv_snapshot', 'forged-import', CURRENT_TIMESTAMP)
            """), {
                "id": UUID("30000000-0000-0000-0000-000000000007"),
                "tenant_b": TENANT_B,
                "product_a": PRODUCT_A,
            })

    with pytest.raises(DBAPIError):
        with migrated_database.begin() as connection:
            connection.execute(text("""
                INSERT INTO inventory_movements
                    (id, tenant_id, balance_id, variant_id, location_id,
                     actor_type, quantity_before, quantity_delta, quantity_after,
                     reason, source_kind, idempotency_key)
                VALUES
                    (:id, :tenant_a, :balance_a, :wrong_variant, :location_a,
                     'system', 3, 1, 4, 'Forged relationship', 'manual', 'forged-movement')
            """), {
                "id": UUID("30000000-0000-0000-0000-000000000008"),
                "tenant_a": TENANT_A,
                "balance_a": BALANCE_A,
                "wrong_variant": VARIANT_A_2,
                "location_a": LOCATION_A,
            })


def test_import_preview_is_scanned_classified_and_tenant_isolated(migrated_database):
    scan_calls = []

    def scanner(content):
        scan_calls.append(content)

    content = (
        "product_name,variant_name,sku,location_code,location_name,quantity,"
        "low_stock_threshold,variant_options,base_price_bdt,expected_record_version\n"
        'Tenant A Shirt,Medium,A-SHIRT-M,DHAKA-A,Tenant A Warehouse,3,5,{},1250.00,1\n'
        "New Product,Default,NEW-SKU,DHAKA-A,Tenant A Warehouse,8,2,{},500.00,\n"
        "Bad Product,Default,BAD-SKU,DHAKA-A,Tenant A Warehouse,-1,2,{},500.00,\n"
    ).encode()
    preview = database_import_previewer(migrated_database, scanner)(
        authority_a(), "merchant.csv", "text/csv", content
    )

    assert scan_calls == [content]
    assert preview.status == "needs_correction"
    assert preview.apply_enabled is False
    assert preview.counts.model_dump() == {
        "total": 3,
        "valid": 2,
        "errors": 1,
        "new": 1,
        "changes": 0,
        "conflicts": 0,
        "unchanged": 1,
    }
    report = database_error_reporter(migrated_database)(authority_a(), preview.preview_id)
    assert report.startswith(b"row_number,column,error_code,message\n")
    assert b"-1" not in report

    with pytest.raises(ImportRejected):
        database_error_reporter(migrated_database)(authority_b(), preview.preview_id)

    with tenant_transaction(migrated_database, authority_a()) as connection:
        stored = connection.execute(
            text("SELECT status, content_sha256 FROM inventory_import_previews WHERE id = :id"),
            {"id": preview.preview_id},
        ).one()
        assert stored.status == "needs_correction"
        assert len(stored.content_sha256) == 64
        error_count = connection.execute(
            text("SELECT COUNT(*) FROM inventory_import_errors")
        ).scalar_one()
        assert error_count == 1
        assert connection.execute(text("SELECT COUNT(*) FROM products")).scalar_one() == 1
        balance_count = connection.execute(
            text("SELECT COUNT(*) FROM inventory_balances")
        ).scalar_one()
        assert balance_count == 2


def test_runtime_cannot_mutate_preview_metadata_or_forge_tenant(migrated_database):
    with pytest.raises(DBAPIError):
        with tenant_transaction(migrated_database, authority_a()) as connection:
            connection.execute(text("DELETE FROM inventory_import_previews"))

    with pytest.raises(DBAPIError):
        with tenant_transaction(migrated_database, authority_a()) as connection:
            connection.execute(
                text("""
                    INSERT INTO inventory_import_previews
                        (id, tenant_id, membership_id, original_filename,
                         content_sha256, byte_size, status, total_rows, valid_rows,
                         error_rows, new_rows, change_rows, conflict_rows,
                         unchanged_rows, expires_at)
                    VALUES
                        (:id, :tenant_b, :membership_b, 'forged.csv', :digest,
                         1, 'ready', 0, 0, 0, 0, 0, 0, 0,
                         CURRENT_TIMESTAMP + INTERVAL '1 hour')
                """),
                {
                    "id": UUID("30000000-0000-0000-0000-000000000099"),
                    "tenant_b": TENANT_B,
                    "membership_b": MEMBERSHIP_B,
                    "digest": "0" * 64,
                },
            )


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

from pathlib import Path
import re

from alembic import command
from alembic.config import Config


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def test_initial_migration_renders_required_rls_contract(monkeypatch, capsys):
    monkeypatch.setenv(
        "BIZPILOT_DATABASE_URL",
        "postgresql+psycopg://migration:unused@localhost/bizpilot_contract",
    )
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    command.upgrade(config, "head", sql=True)
    sql = capsys.readouterr().out

    for table in ("tenants", "identities", "memberships", "platform_staff", "locations", "audit_events"):
        assert f"CREATE TABLE {table}" in sql
    assert "CREATE ROLE" not in sql
    assert "ENABLE ROW LEVEL SECURITY" in sql
    assert "FORCE ROW LEVEL SECURITY" in sql
    assert "CREATE POLICY locations_runtime_policy" in sql
    assert "CREATE POLICY audit_events_runtime_insert" in sql
    assert "SECURITY DEFINER" in sql
    assert "NOBYPASSRLS" not in sql
    assert "GRANT SELECT, INSERT, UPDATE, DELETE ON locations TO bizpilot_runtime" in sql
    assert 'ALTER TABLE "locations" FORCE ROW LEVEL SECURITY' in sql
    assert 'ALTER TABLE "audit_events" FORCE ROW LEVEL SECURITY' in sql


def test_role_bootstrap_is_restricted_and_contains_no_credentials():
    sql = (BACKEND_ROOT / "sql" / "roles.sql").read_text(encoding="utf-8")
    assert "NOBYPASSRLS" in sql
    assert "NOSUPERUSER" in sql
    assert "NOCREATEROLE" in sql
    assert "NOLOGIN" in sql
    executable_sql = re.sub(r"--.*$", "", sql, flags=re.MULTILINE)
    assert "PASSWORD" not in executable_sql.upper()

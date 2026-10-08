import pytest

from backend.app.authorization import MerchantRole, TenantAuthority
from backend.app.database import database_url, tenant_transaction


def test_database_url_is_required_and_postgresql_only(monkeypatch):
    monkeypatch.delenv("BIZPILOT_DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="required"):
        database_url()
    monkeypatch.setenv("BIZPILOT_DATABASE_URL", "sqlite:///unsafe.db")
    with pytest.raises(RuntimeError, match="requires PostgreSQL"):
        database_url()


def test_tenant_context_is_transaction_local_and_parameterized():
    class FakeConnection:
        def __init__(self):
            self.statements = []

        def execute(self, statement, parameters=None):
            self.statements.append((str(statement), parameters or {}))

    class FakeTransaction:
        def __init__(self, connection):
            self.connection = connection

        def __enter__(self):
            return self.connection

        def __exit__(self, *_args):
            return False

    class FakeEngine:
        def __init__(self):
            self.connection = FakeConnection()

        def begin(self):
            return FakeTransaction(self.connection)

    engine = FakeEngine()
    authority = TenantAuthority(
        identity_id="00000000-0000-0000-0000-000000000001",
        membership_id="00000000-0000-0000-0000-000000000002",
        tenant_id="00000000-0000-0000-0000-000000000003",
        role=MerchantRole.OWNER,
        permission_version=7,
    )
    with tenant_transaction(engine, authority):
        pass

    assert engine.connection.statements[0][0] == "SET LOCAL ROLE bizpilot_runtime"
    statement, parameters = engine.connection.statements[1]
    assert "set_config" in statement
    assert authority.tenant_id not in statement
    assert parameters == {"name": "app.tenant_id", "value": authority.tenant_id}


def test_tenant_context_rejects_non_database_identifiers():
    authority = TenantAuthority(
        identity_id="https://identity.example|subject",
        membership_id="membership-a",
        tenant_id="tenant-a",
        role=MerchantRole.OWNER,
        permission_version=1,
    )
    with pytest.raises(ValueError, match="Invalid tenant authority"):
        with tenant_transaction(object(), authority):
            pass

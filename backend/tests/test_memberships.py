from datetime import datetime, timezone
from uuid import UUID

import pytest
from sqlalchemy.exc import OperationalError

from backend.app.authorization import AuthorizationDenied, MerchantRole
from backend.app.identity import VerifiedIdentity
from backend.app.memberships import (
    MembershipLookupUnavailable,
    auth_database_url,
    persistent_authority_resolver,
)


TENANT_ID = "10000000-0000-0000-0000-000000000001"
IDENTITY = VerifiedIdentity(
    "https://identity.example/",
    "merchant-user-1",
    datetime.now(timezone.utc),
    datetime.now(timezone.utc),
)


class FakeResult:
    def __init__(self, row):
        self.row = row

    def mappings(self):
        return self

    def one_or_none(self):
        return self.row


class FakeConnection:
    def __init__(self, row=None, error=None):
        self.row = row
        self.error = error
        self.calls = []

    def execute(self, statement, parameters=None):
        self.calls.append((str(statement), parameters or {}))
        if self.error:
            raise self.error
        return FakeResult(self.row)


class FakeTransaction:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self.connection

    def __exit__(self, *_args):
        return False


class FakeEngine:
    def __init__(self, connection):
        self.connection = connection

    def begin(self):
        return FakeTransaction(self.connection)


def test_membership_lookup_is_role_restricted_and_parameterized():
    connection = FakeConnection({
        "identity_id": UUID("10000000-0000-0000-0000-000000000002"),
        "membership_id": UUID("10000000-0000-0000-0000-000000000003"),
        "tenant_id": UUID(TENANT_ID),
        "role": "operations",
        "permission_version": 4,
    })
    authority = persistent_authority_resolver(FakeEngine(connection))(IDENTITY, TENANT_ID)
    assert authority.role == MerchantRole.OPERATIONS
    assert authority.permission_version == 4
    assert connection.calls[0][0] == "SET LOCAL ROLE bizpilot_authenticator"
    statement, parameters = connection.calls[1]
    assert "bizpilot_resolve_membership" in statement
    assert IDENTITY.subject not in statement
    assert parameters["subject"] == IDENTITY.subject
    assert parameters["tenant_id"] == UUID(TENANT_ID)


def test_invalid_or_missing_membership_fails_without_disclosure():
    resolver = persistent_authority_resolver(FakeEngine(FakeConnection(None)))
    with pytest.raises(AuthorizationDenied, match="Access denied for this workspace"):
        resolver(IDENTITY, TENANT_ID)
    with pytest.raises(AuthorizationDenied, match="Access denied for this workspace"):
        resolver(IDENTITY, "not-a-tenant")


def test_database_failure_becomes_sanitized_unavailable_error():
    error = OperationalError("SELECT secret", {}, Exception("database-secret"))
    resolver = persistent_authority_resolver(FakeEngine(FakeConnection(error=error)))
    with pytest.raises(MembershipLookupUnavailable, match="Membership lookup failed"):
        resolver(IDENTITY, TENANT_ID)


def test_auth_database_url_is_separate_and_postgresql_only(monkeypatch):
    monkeypatch.delenv("BIZPILOT_AUTH_DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="required"):
        auth_database_url()
    monkeypatch.setenv("BIZPILOT_AUTH_DATABASE_URL", "sqlite:///unsafe.db")
    with pytest.raises(RuntimeError, match="requires PostgreSQL"):
        auth_database_url()

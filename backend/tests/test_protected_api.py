from datetime import datetime, timezone
import logging

from fastapi.testclient import TestClient

from backend.app.api_auth import AuthServices
from backend.app.authorization import AuthorizationDenied, MerchantRole, TenantAuthority
from backend.app.identity import (
    AuthenticationDenied,
    IdentityProviderUnavailable,
    VerifiedIdentity,
)
from backend.app.main import create_app


TENANT_ID = "10000000-0000-0000-0000-000000000001"


class FakeVerifier:
    def __init__(self, denied=False, unavailable=False):
        self.denied = denied
        self.unavailable = unavailable

    def verify(self, token):
        if self.unavailable:
            raise IdentityProviderUnavailable("private provider response")
        if self.denied:
            raise AuthenticationDenied("provider detail must not escape")
        now = datetime.now(timezone.utc)
        return VerifiedIdentity("https://identity.example/", "private-subject", now, now)


class MutableResolver:
    def __init__(self):
        self.active = True
        self.calls = 0

    def __call__(self, _identity, active_tenant_id):
        self.calls += 1
        if not self.active or active_tenant_id != TENANT_ID:
            raise AuthorizationDenied("private membership detail")
        return TenantAuthority(
            identity_id="10000000-0000-0000-0000-000000000002",
            membership_id="10000000-0000-0000-0000-000000000003",
            tenant_id=TENANT_ID,
            role=MerchantRole.OWNER,
            permission_version=3,
        )


def client(verifier=None, resolver=None):
    services = AuthServices(verifier or FakeVerifier(), resolver or MutableResolver())
    return TestClient(create_app(services))


def headers(tenant=TENANT_ID, token="private-token-value"):
    return {"Authorization": f"Bearer {token}", "X-BizPilot-Tenant": tenant}


def test_protected_workspace_requires_bearer_and_selector():
    response = client().get("/api/v1/workspace")
    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required."}
    assert response.headers["www-authenticate"] == "Bearer"

    response = client().get(
        "/api/v1/workspace",
        headers={"Authorization": "Bearer private-token-value"},
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Select a workspace."}


def test_protected_workspace_returns_current_server_authority_only():
    response = client().get("/api/v1/workspace", headers=headers())
    assert response.status_code == 200
    assert response.json() == {
        "workspace_id": TENANT_ID,
        "role": "owner",
        "permission_version": 3,
    }
    assert len(response.headers["x-correlation-id"]) == 32


def test_invalid_token_and_membership_are_sanitized(caplog):
    caplog.set_level(logging.WARNING, logger="bizpilot.security")
    response = client(verifier=FakeVerifier(denied=True)).get(
        "/api/v1/workspace", headers=headers()
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid authentication token."}

    response = client().get(
        "/api/v1/workspace",
        headers=headers("20000000-0000-0000-0000-000000000001"),
    )
    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied for this workspace."}
    assert "private-token-value" not in caplog.text
    assert "private-subject" not in caplog.text
    assert "private membership detail" not in caplog.text


def test_membership_revocation_is_rechecked_on_every_request():
    resolver = MutableResolver()
    test_client = client(resolver=resolver)
    assert test_client.get("/api/v1/workspace", headers=headers()).status_code == 200
    resolver.active = False
    assert test_client.get("/api/v1/workspace", headers=headers()).status_code == 403
    assert resolver.calls == 2


def test_identity_provider_outage_is_sanitized_as_unavailable(caplog):
    caplog.set_level(logging.WARNING, logger="bizpilot.security")
    response = client(verifier=FakeVerifier(unavailable=True)).get(
        "/api/v1/workspace", headers=headers()
    )
    assert response.status_code == 503
    assert response.json() == {"detail": "Authentication service unavailable."}
    assert "private provider response" not in caplog.text


def test_missing_server_auth_configuration_is_sanitized(monkeypatch):
    for name in (
        "BIZPILOT_OIDC_ISSUER",
        "BIZPILOT_OIDC_AUDIENCE",
        "BIZPILOT_OIDC_JWKS_URL",
        "BIZPILOT_AUTH_DATABASE_URL",
    ):
        monkeypatch.delenv(name, raising=False)
    response = TestClient(create_app()).get("/api/v1/workspace", headers=headers())
    assert response.status_code == 503
    assert response.json() == {"detail": "Authentication service unavailable."}

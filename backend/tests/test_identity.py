from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives.asymmetric import rsa
import jwt
import pytest

from backend.app.identity import (
    AuthenticationDenied,
    IdentityConfigurationError,
    OIDCSettings,
    OIDCVerifier,
)


PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PUBLIC_KEY = PRIVATE_KEY.public_key()
SETTINGS = OIDCSettings(
    issuer="https://identity.example/",
    audience="bizpilot-api",
    jwks_url="https://identity.example/.well-known/jwks.json",
)


def token(**overrides):
    now = datetime.now(timezone.utc)
    claims = {
        "iss": SETTINGS.issuer,
        "sub": "merchant-user-1",
        "aud": SETTINGS.audience,
        "iat": now,
        "exp": now + timedelta(minutes=10),
    }
    claims.update(overrides)
    return jwt.encode(claims, PRIVATE_KEY, algorithm="RS256", headers={"kid": "test-key"})


def verifier(settings=SETTINGS):
    return OIDCVerifier(settings, signing_key_resolver=lambda _token: PUBLIC_KEY)


def test_valid_oidc_token_returns_verified_external_identity():
    identity = verifier().verify(token())
    assert identity.issuer == SETTINGS.issuer
    assert identity.subject == "merchant-user-1"
    assert identity.issued_at.tzinfo == timezone.utc


@pytest.mark.parametrize(
    "override",
    [
        {"iss": "https://attacker.example/"},
        {"aud": "another-api"},
        {"exp": datetime.now(timezone.utc) - timedelta(minutes=2)},
        {"sub": ""},
    ],
)
def test_invalid_oidc_claims_fail_closed(override):
    with pytest.raises(AuthenticationDenied, match="Invalid authentication token"):
        verifier().verify(token(**override))


def test_invalid_signature_and_algorithm_fail_closed():
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.now(timezone.utc)
    wrong_signature = jwt.encode(
        {
            "iss": SETTINGS.issuer,
            "sub": "merchant-user-1",
            "aud": SETTINGS.audience,
            "iat": now,
            "exp": now + timedelta(minutes=10),
        },
        other_key,
        algorithm="RS256",
    )
    with pytest.raises(AuthenticationDenied):
        verifier().verify(wrong_signature)

    hs_token = jwt.encode(
        {
            "iss": SETTINGS.issuer,
            "sub": "merchant-user-1",
            "aud": SETTINGS.audience,
            "iat": now,
            "exp": now + timedelta(minutes=10),
        },
        "unsafe-shared-secret-that-is-long-enough",
        algorithm="HS256",
    )
    with pytest.raises(AuthenticationDenied):
        verifier().verify(hs_token)


def test_old_token_is_rejected_even_when_expiry_is_later():
    old = datetime.now(timezone.utc) - timedelta(hours=2)
    with pytest.raises(AuthenticationDenied):
        verifier().verify(token(iat=old, exp=datetime.now(timezone.utc) + timedelta(minutes=5)))


def test_oidc_settings_require_safe_complete_urls(monkeypatch):
    monkeypatch.setenv("BIZPILOT_OIDC_ISSUER", "http://identity.example")
    monkeypatch.setenv("BIZPILOT_OIDC_AUDIENCE", "bizpilot-api")
    monkeypatch.setenv("BIZPILOT_OIDC_JWKS_URL", "https://identity.example/jwks.json")
    with pytest.raises(IdentityConfigurationError, match="HTTPS"):
        OIDCSettings.from_env()

    monkeypatch.setenv("BIZPILOT_OIDC_ISSUER", "https://identity.example/")
    monkeypatch.delenv("BIZPILOT_OIDC_AUDIENCE")
    with pytest.raises(IdentityConfigurationError, match="incomplete"):
        OIDCSettings.from_env()

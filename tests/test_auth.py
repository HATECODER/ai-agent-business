from datetime import datetime, timedelta, timezone

import pytest

from agent import ask_copilot
from security.auth import ActorContext, AuthorizationError, actor_from_claims, require_owner


ISSUER = "https://identity.example"
SUBJECT = "owner-123"


def configure_pilot(monkeypatch):
    monkeypatch.setenv("BIZPILOT_DEPLOYMENT_MODE", "pilot")
    monkeypatch.setenv("BIZPILOT_DATA_MODE", "synthetic")
    monkeypatch.setenv("BIZPILOT_OWNER_SUBJECTS", f"{ISSUER}|{SUBJECT}")


def test_pilot_rejects_missing_and_unlisted_identity(monkeypatch):
    configure_pilot(monkeypatch)
    now = datetime.now(timezone.utc)
    with pytest.raises(AuthorizationError):
        require_owner(None, now)
    with pytest.raises(AuthorizationError):
        actor_from_claims({"iss": ISSUER, "sub": "someone-else"}, now, now)
    with pytest.raises(AuthorizationError):
        actor_from_claims({"sub": SUBJECT}, now, now)


def test_pilot_rechecks_revocation_and_expiry(monkeypatch):
    configure_pilot(monkeypatch)
    now = datetime.now(timezone.utc)
    actor = actor_from_claims({"iss": ISSUER, "sub": SUBJECT}, now, now)
    assert require_owner(actor, now).actor_id == f"{ISSUER}|{SUBJECT}"
    monkeypatch.setenv("BIZPILOT_OWNER_SUBJECTS", "")
    with pytest.raises(AuthorizationError):
        require_owner(actor, now)

    monkeypatch.setenv("BIZPILOT_OWNER_SUBJECTS", f"{ISSUER}|{SUBJECT}")
    expired = ActorContext(ISSUER, SUBJECT, "Owner", now - timedelta(seconds=1))
    with pytest.raises(AuthorizationError):
        require_owner(expired, now)


def test_denied_actor_cannot_reach_model(monkeypatch, seeded_db):
    configure_pilot(monkeypatch)
    called = False

    def forbidden_model(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("model should not run")

    monkeypatch.setattr("agent.Runner.run_sync", forbidden_model)
    with pytest.raises(AuthorizationError):
        ask_copilot("show inventory", db_path=seeded_db)
    assert called is False

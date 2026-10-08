"""Small fail-closed owner authorization boundary.

Authentication is performed by Streamlit OIDC. This module performs the
application authorization check and can be tested without a browser.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Mapping, Any

from config import deployment_mode, owner_subject_allowlist, session_hours


class AuthorizationError(PermissionError):
    """The current actor is not permitted to use the pilot."""


@dataclass(frozen=True)
class ActorContext:
    issuer: str
    subject: str
    display_name: str
    session_expires_at: datetime
    role: str = "owner"

    @property
    def actor_id(self) -> str:
        return f"{self.issuer}|{self.subject}"


def demo_actor(now: datetime | None = None) -> ActorContext:
    current = now or datetime.now(timezone.utc)
    return ActorContext(
        issuer="local-demo",
        subject="fictional-owner",
        display_name="Demo owner",
        session_expires_at=current + timedelta(hours=12),
    )


def actor_from_claims(
    claims: Mapping[str, Any],
    session_started_at: datetime,
    now: datetime | None = None,
) -> ActorContext:
    """Build and authorize an actor from verified OIDC claims.

    Email and display name are presentation fields only. Authorization uses
    the immutable issuer/subject pair supplied by the identity provider.
    """
    current = now or datetime.now(timezone.utc)
    issuer = str(claims.get("iss", "")).strip()
    subject = str(claims.get("sub", "")).strip()
    if not issuer or not subject:
        raise AuthorizationError("The identity provider did not supply issuer and subject claims.")
    if (issuer, subject) not in owner_subject_allowlist():
        raise AuthorizationError("This identity is not allowlisted for the BizPilot pilot.")

    application_expiry = session_started_at + timedelta(hours=session_hours())
    provider_expiry = _provider_expiry(claims.get("exp"))
    effective_expiry = min(application_expiry, provider_expiry) if provider_expiry else application_expiry
    if current >= effective_expiry:
        raise AuthorizationError("The BizPilot session has expired. Sign in again.")

    return ActorContext(
        issuer=issuer,
        subject=subject,
        display_name=str(claims.get("name") or claims.get("email") or "Owner"),
        session_expires_at=effective_expiry,
    )


def require_owner(actor: ActorContext | None, now: datetime | None = None) -> ActorContext:
    """Recheck authorization at every read or action boundary."""
    current = now or datetime.now(timezone.utc)
    if deployment_mode() == "demo":
        actor = actor or demo_actor(current)
        if actor.session_expires_at <= current:
            raise AuthorizationError("The demo session has expired.")
        return actor
    if actor is None:
        raise AuthorizationError("Sign in with an allowlisted owner account.")
    if actor.role != "owner":
        raise AuthorizationError("Owner access is required.")
    if (actor.issuer, actor.subject) not in owner_subject_allowlist():
        raise AuthorizationError("This identity is no longer allowlisted.")
    if actor.session_expires_at <= current:
        raise AuthorizationError("The BizPilot session has expired. Sign in again.")
    return actor


def _provider_expiry(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        return datetime.fromtimestamp(float(value), timezone.utc)
    except (TypeError, ValueError, OverflowError) as error:
        raise AuthorizationError("The identity provider supplied an invalid expiry claim.") from error

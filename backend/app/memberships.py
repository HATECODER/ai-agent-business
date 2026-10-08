"""Persistent identity and membership resolution through a restricted DB role."""

from collections.abc import Callable
import os
from uuid import UUID

from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError

from backend.app.authorization import AuthorizationDenied, MerchantRole, TenantAuthority
from backend.app.database import create_database_engine
from backend.app.identity import VerifiedIdentity


class MembershipLookupUnavailable(RuntimeError):
    """Membership authority could not be checked safely."""


AuthorityResolver = Callable[[VerifiedIdentity, str], TenantAuthority]


def auth_database_url() -> str:
    value = os.getenv("BIZPILOT_AUTH_DATABASE_URL", "").strip()
    if not value:
        raise RuntimeError("BIZPILOT_AUTH_DATABASE_URL is required for membership lookup.")
    if not value.startswith(("postgresql://", "postgresql+psycopg://")):
        raise RuntimeError("Membership lookup requires PostgreSQL.")
    return value


def create_auth_engine(url: str | None = None) -> Engine:
    return create_database_engine(url or auth_database_url())


def persistent_authority_resolver(engine: Engine) -> AuthorityResolver:
    def resolve(identity: VerifiedIdentity, active_tenant_id: str) -> TenantAuthority:
        try:
            tenant_uuid = UUID(active_tenant_id)
        except (ValueError, TypeError, AttributeError) as error:
            raise AuthorizationDenied("Access denied for this workspace.") from error

        try:
            with engine.begin() as connection:
                connection.execute(text("SET LOCAL ROLE bizpilot_authenticator"))
                row = connection.execute(
                    text("""
                        SELECT identity_id, membership_id, tenant_id, role, permission_version
                        FROM bizpilot_resolve_membership(
                            :issuer, :subject, :tenant_id, :token_issued_at
                        )
                    """),
                    {
                        "issuer": identity.issuer,
                        "subject": identity.subject,
                        "tenant_id": tenant_uuid,
                        "token_issued_at": identity.issued_at,
                    },
                ).mappings().one_or_none()
        except SQLAlchemyError as error:
            raise MembershipLookupUnavailable("Membership lookup failed.") from error

        if row is None:
            raise AuthorizationDenied("Access denied for this workspace.")
        try:
            return TenantAuthority(
                identity_id=str(row["identity_id"]),
                membership_id=str(row["membership_id"]),
                tenant_id=str(row["tenant_id"]),
                role=MerchantRole(row["role"]),
                permission_version=int(row["permission_version"]),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise MembershipLookupUnavailable("Membership lookup returned invalid authority.") from error

    return resolve

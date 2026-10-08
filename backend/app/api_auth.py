"""FastAPI authentication and active-tenant dependencies."""

from dataclasses import dataclass
import logging

from fastapi import HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.authorization import AuthorizationDenied, TenantAuthority
from backend.app.identity import (
    AuthenticationDenied,
    IdentityConfigurationError,
    IdentityProviderUnavailable,
    OIDCSettings,
    OIDCVerifier,
)
from backend.app.memberships import (
    AuthorityResolver,
    MembershipLookupUnavailable,
    create_auth_engine,
    persistent_authority_resolver,
)


LOGGER = logging.getLogger("bizpilot.security")
BEARER = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthServices:
    verifier: OIDCVerifier
    resolve_authority: AuthorityResolver


def auth_services_from_env() -> AuthServices:
    verifier = OIDCVerifier(OIDCSettings.from_env())
    resolver = persistent_authority_resolver(create_auth_engine())
    return AuthServices(verifier, resolver)


def _deny(request: Request, category: str, status_code: int, detail: str) -> None:
    correlation_id = getattr(request.state, "correlation_id", "unavailable")
    LOGGER.warning(
        "access_denied category=%s correlation_id=%s",
        category,
        correlation_id,
    )
    headers = {"WWW-Authenticate": "Bearer"} if status_code == 401 else None
    raise HTTPException(status_code=status_code, detail=detail, headers=headers)


def _services(request: Request) -> AuthServices:
    services = request.app.state.auth_services
    if services is not None:
        return services
    try:
        services = auth_services_from_env()
    except (IdentityConfigurationError, RuntimeError):
        _deny(request, "auth_configuration", 503, "Authentication service unavailable.")
    request.app.state.auth_services = services
    return services


def require_tenant_authority(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(BEARER),
) -> TenantAuthority:
    if credentials is None or credentials.scheme.lower() != "bearer":
        _deny(request, "missing_bearer", 401, "Authentication required.")
    active_tenant_id = request.headers.get("X-BizPilot-Tenant", "").strip()
    if not active_tenant_id:
        _deny(request, "missing_workspace", 400, "Select a workspace.")

    services = _services(request)
    try:
        identity = services.verifier.verify(credentials.credentials)
    except AuthenticationDenied:
        _deny(request, "invalid_token", 401, "Invalid authentication token.")
    except IdentityProviderUnavailable:
        _deny(request, "identity_provider_unavailable", 503, "Authentication service unavailable.")
    try:
        return services.resolve_authority(identity, active_tenant_id)
    except AuthorizationDenied:
        _deny(request, "membership_denied", 403, "Access denied for this workspace.")
    except MembershipLookupUnavailable:
        _deny(request, "membership_unavailable", 503, "Authentication service unavailable.")

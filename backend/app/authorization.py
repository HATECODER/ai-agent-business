"""Tenant-scoped authorization policy for the commercial R1 backend.

Authentication verifies an external identity. This module then resolves one
active merchant membership and enforces the fixed R1 role grants. It contains
no HTTP-header or token parsing so callers cannot accidentally treat a claimed
tenant ID as authority.
"""

from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Iterable, Mapping


class AuthorizationDenied(PermissionError):
    """A sanitized authorization failure safe to return through an API."""


class MerchantRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    OPERATIONS = "operations"
    GROWTH = "growth"
    FINANCE_VIEWER = "finance_viewer"
    VIEWER = "viewer"


class MembershipStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


class GrantScope(StrEnum):
    ALL = "all"
    DOMAIN = "domain"
    OWN = "own"


class Permission(StrEnum):
    WORKSPACE_READ = "workspace.read"
    WORKSPACE_UPDATE = "workspace.update"
    WORKSPACE_CLOSE = "workspace.close"
    MEMBERS_READ = "members.read"
    MEMBERS_INVITE = "members.invite"
    MEMBERS_MANAGE = "members.manage"
    MEMBERS_ASSIGN_OWNER = "members.assign_owner"
    BILLING_READ = "billing.read"
    BILLING_MANAGE = "billing.manage"
    CONNECTIONS_READ = "connections.read"
    CONNECTIONS_MANAGE = "connections.manage"
    PRODUCTS_READ = "products.read"
    PRODUCTS_MANAGE = "products.manage"
    INVENTORY_READ = "inventory.read"
    INVENTORY_ADJUST = "inventory.adjust"
    INVENTORY_IMPORT = "inventory.import"
    INVENTORY_EXPORT = "inventory.export"
    TASKS_READ = "tasks.read"
    TASKS_MANAGE = "tasks.manage"
    CUSTOMER_SEGMENTS_READ = "customers.segment.read"
    CUSTOMER_DETAILS_READ = "customers.detail.read"
    CUSTOMERS_EXPORT = "customers.export"
    CAMPAIGNS_READ = "campaigns.read"
    CAMPAIGNS_DRAFT = "campaigns.draft"
    FINANCE_SUMMARY_READ = "finance.summary.read"
    FINANCE_EXPORT = "finance.export"
    APPROVALS_READ = "approvals.read"
    APPROVE_OPERATIONS = "approvals.operations.approve"
    APPROVE_CAMPAIGN_DRAFT = "approvals.campaign_draft.approve"
    AUDIT_READ = "audit.read"
    AUDIT_EXPORT = "audit.export"
    COPILOT_USE = "copilot.use"
    AI_SETTINGS_MANAGE = "ai.settings.manage"


class PlatformRole(StrEnum):
    OWNER = "platform_owner"
    OPERATOR = "platform_operator"
    SUPPORT = "support_agent"
    SECURITY_RESPONDER = "security_responder"


class PlatformPermission(StrEnum):
    PLATFORM_CONFIGURE = "platform.configure"
    TENANT_METADATA_READ = "tenant.metadata.read"
    SERVICE_HEALTH_READ = "service_health.read"
    CONNECTION_FAILURES_READ = "connection_failures.read"
    SUPPORT_ACCESS_REQUEST = "support_access.request"
    SUPPORT_ACCESS_APPROVE = "support_access.approve"
    TENANT_SUSPEND = "tenant.suspend"
    CREDENTIALS_REVOKE = "credentials.revoke"
    SECURITY_AUDIT_READ = "security_audit.read"
    BILLING_CONFIGURE = "billing.configure"


def _grants(*permissions: Permission) -> dict[Permission, GrantScope]:
    return {permission: GrantScope.ALL for permission in permissions}


_OWNER_GRANTS = _grants(*Permission)
_ADMIN_GRANTS = _grants(
    Permission.WORKSPACE_READ,
    Permission.WORKSPACE_UPDATE,
    Permission.MEMBERS_READ,
    Permission.MEMBERS_INVITE,
    Permission.MEMBERS_MANAGE,
    Permission.CONNECTIONS_READ,
    Permission.CONNECTIONS_MANAGE,
    Permission.PRODUCTS_READ,
    Permission.PRODUCTS_MANAGE,
    Permission.INVENTORY_READ,
    Permission.INVENTORY_ADJUST,
    Permission.INVENTORY_IMPORT,
    Permission.INVENTORY_EXPORT,
    Permission.TASKS_READ,
    Permission.TASKS_MANAGE,
    Permission.CUSTOMER_SEGMENTS_READ,
    Permission.CUSTOMER_DETAILS_READ,
    Permission.CAMPAIGNS_READ,
    Permission.CAMPAIGNS_DRAFT,
    Permission.FINANCE_SUMMARY_READ,
    Permission.APPROVALS_READ,
    Permission.APPROVE_OPERATIONS,
    Permission.APPROVE_CAMPAIGN_DRAFT,
    Permission.AUDIT_READ,
    Permission.COPILOT_USE,
    Permission.AI_SETTINGS_MANAGE,
)
_OPERATIONS_GRANTS = _grants(
    Permission.WORKSPACE_READ,
    Permission.PRODUCTS_READ,
    Permission.PRODUCTS_MANAGE,
    Permission.INVENTORY_READ,
    Permission.INVENTORY_ADJUST,
    Permission.INVENTORY_IMPORT,
    Permission.INVENTORY_EXPORT,
    Permission.TASKS_READ,
    Permission.TASKS_MANAGE,
)
_OPERATIONS_GRANTS.update({
    Permission.CONNECTIONS_READ: GrantScope.DOMAIN,
    Permission.APPROVALS_READ: GrantScope.DOMAIN,
    Permission.APPROVE_OPERATIONS: GrantScope.DOMAIN,
    Permission.AUDIT_READ: GrantScope.DOMAIN,
    Permission.COPILOT_USE: GrantScope.DOMAIN,
})
_GROWTH_GRANTS = _grants(
    Permission.WORKSPACE_READ,
    Permission.PRODUCTS_READ,
    Permission.INVENTORY_READ,
    Permission.CUSTOMER_SEGMENTS_READ,
    Permission.CAMPAIGNS_READ,
    Permission.CAMPAIGNS_DRAFT,
)
_GROWTH_GRANTS.update({
    Permission.CONNECTIONS_READ: GrantScope.DOMAIN,
    Permission.TASKS_READ: GrantScope.OWN,
    Permission.TASKS_MANAGE: GrantScope.OWN,
    Permission.CUSTOMER_DETAILS_READ: GrantScope.DOMAIN,
    Permission.APPROVALS_READ: GrantScope.DOMAIN,
    Permission.APPROVE_CAMPAIGN_DRAFT: GrantScope.DOMAIN,
    Permission.AUDIT_READ: GrantScope.DOMAIN,
    Permission.COPILOT_USE: GrantScope.DOMAIN,
})
_FINANCE_GRANTS = _grants(
    Permission.WORKSPACE_READ,
    Permission.FINANCE_SUMMARY_READ,
    Permission.FINANCE_EXPORT,
)
_FINANCE_GRANTS[Permission.COPILOT_USE] = GrantScope.DOMAIN
_VIEWER_GRANTS = _grants(
    Permission.WORKSPACE_READ,
    Permission.PRODUCTS_READ,
    Permission.INVENTORY_READ,
    Permission.TASKS_READ,
    Permission.CAMPAIGNS_READ,
)
_VIEWER_GRANTS[Permission.COPILOT_USE] = GrantScope.DOMAIN


ROLE_GRANTS: Mapping[MerchantRole, Mapping[Permission, GrantScope]] = MappingProxyType({
    MerchantRole.OWNER: MappingProxyType(_OWNER_GRANTS),
    MerchantRole.ADMIN: MappingProxyType(_ADMIN_GRANTS),
    MerchantRole.OPERATIONS: MappingProxyType(_OPERATIONS_GRANTS),
    MerchantRole.GROWTH: MappingProxyType(_GROWTH_GRANTS),
    MerchantRole.FINANCE_VIEWER: MappingProxyType(_FINANCE_GRANTS),
    MerchantRole.VIEWER: MappingProxyType(_VIEWER_GRANTS),
})


def _platform_grants(*permissions: PlatformPermission) -> frozenset[PlatformPermission]:
    return frozenset(permissions)


PLATFORM_ROLE_GRANTS: Mapping[PlatformRole, frozenset[PlatformPermission]] = MappingProxyType({
    PlatformRole.OWNER: _platform_grants(*PlatformPermission),
    PlatformRole.OPERATOR: _platform_grants(
        PlatformPermission.TENANT_METADATA_READ,
        PlatformPermission.SERVICE_HEALTH_READ,
        PlatformPermission.CONNECTION_FAILURES_READ,
        PlatformPermission.SUPPORT_ACCESS_REQUEST,
        PlatformPermission.TENANT_SUSPEND,
        PlatformPermission.CREDENTIALS_REVOKE,
        PlatformPermission.SECURITY_AUDIT_READ,
    ),
    PlatformRole.SUPPORT: _platform_grants(
        PlatformPermission.TENANT_METADATA_READ,
        PlatformPermission.SERVICE_HEALTH_READ,
        PlatformPermission.CONNECTION_FAILURES_READ,
        PlatformPermission.SUPPORT_ACCESS_REQUEST,
    ),
    PlatformRole.SECURITY_RESPONDER: _platform_grants(
        PlatformPermission.TENANT_METADATA_READ,
        PlatformPermission.SERVICE_HEALTH_READ,
        PlatformPermission.CONNECTION_FAILURES_READ,
        PlatformPermission.SUPPORT_ACCESS_REQUEST,
        PlatformPermission.TENANT_SUSPEND,
        PlatformPermission.CREDENTIALS_REVOKE,
        PlatformPermission.SECURITY_AUDIT_READ,
    ),
})


@dataclass(frozen=True)
class ExternalIdentity:
    issuer: str
    subject: str

    @property
    def identity_id(self) -> str:
        return f"{self.issuer}|{self.subject}"


@dataclass(frozen=True)
class Membership:
    membership_id: str
    tenant_id: str
    identity_id: str
    role: MerchantRole
    status: MembershipStatus
    permission_version: int


@dataclass(frozen=True)
class TenantAuthority:
    identity_id: str
    membership_id: str
    tenant_id: str
    role: MerchantRole
    permission_version: int


@dataclass(frozen=True)
class PlatformAuthority:
    identity_id: str
    role: PlatformRole


def resolve_tenant_authority(
    identity: ExternalIdentity,
    active_tenant_id: str,
    memberships: Iterable[Membership],
) -> TenantAuthority:
    """Resolve authority only from an exact, active server-side membership."""
    if not identity.issuer.strip() or not identity.subject.strip() or not active_tenant_id.strip():
        raise AuthorizationDenied("Access denied for this workspace.")

    matches = [
        membership
        for membership in memberships
        if membership.identity_id == identity.identity_id
        and membership.tenant_id == active_tenant_id
        and membership.status == MembershipStatus.ACTIVE
    ]
    if len(matches) != 1:
        raise AuthorizationDenied("Access denied for this workspace.")

    membership = matches[0]
    if membership.permission_version < 1:
        raise AuthorizationDenied("Access denied for this workspace.")
    return TenantAuthority(
        identity_id=identity.identity_id,
        membership_id=membership.membership_id,
        tenant_id=membership.tenant_id,
        role=membership.role,
        permission_version=membership.permission_version,
    )


def require_permission(
    authority: TenantAuthority,
    permission: Permission,
    *,
    resource_tenant_id: str | None = None,
    resource_owner_identity_id: str | None = None,
) -> GrantScope:
    """Enforce role grant and optional object tenant/owner scope."""
    if not isinstance(authority, TenantAuthority):
        raise AuthorizationDenied("Permission denied.")
    if resource_tenant_id is not None and resource_tenant_id != authority.tenant_id:
        raise AuthorizationDenied("Resource not found.")

    scope = ROLE_GRANTS.get(authority.role, {}).get(permission)
    if scope is None:
        raise AuthorizationDenied("Permission denied.")
    if scope == GrantScope.OWN and resource_owner_identity_id != authority.identity_id:
        raise AuthorizationDenied("Resource not found.")
    return scope


def require_platform_permission(
    authority: PlatformAuthority,
    permission: PlatformPermission,
) -> None:
    """Enforce platform access without creating merchant authority."""
    if not isinstance(authority, PlatformAuthority):
        raise AuthorizationDenied("Permission denied.")
    if permission not in PLATFORM_ROLE_GRANTS.get(authority.role, frozenset()):
        raise AuthorizationDenied("Permission denied.")

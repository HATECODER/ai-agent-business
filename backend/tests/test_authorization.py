import pytest

from backend.app.authorization import (
    AuthorizationDenied,
    ExternalIdentity,
    GrantScope,
    Membership,
    MembershipStatus,
    MerchantRole,
    Permission,
    PlatformAuthority,
    PlatformPermission,
    PlatformRole,
    PLATFORM_ROLE_GRANTS,
    ROLE_GRANTS,
    require_permission,
    require_platform_permission,
    resolve_tenant_authority,
)


IDENTITY = ExternalIdentity("https://identity.example", "user-1")
IDENTITY_RECORD_ID = "00000000-0000-0000-0000-000000000001"


def membership(tenant_id: str, role: MerchantRole, *, status=MembershipStatus.ACTIVE):
    return Membership(
        membership_id=f"membership-{tenant_id}",
        tenant_id=tenant_id,
        identity_id=IDENTITY_RECORD_ID,
        identity_issuer=IDENTITY.issuer,
        identity_subject=IDENTITY.subject,
        role=role,
        status=status,
        permission_version=1,
    )


def test_role_policy_is_deny_by_default_and_has_all_fixed_roles():
    assert set(ROLE_GRANTS) == set(MerchantRole)
    assert Permission.BILLING_MANAGE in ROLE_GRANTS[MerchantRole.OWNER]
    assert Permission.BILLING_MANAGE not in ROLE_GRANTS[MerchantRole.ADMIN]
    assert Permission.INVENTORY_ADJUST in ROLE_GRANTS[MerchantRole.OPERATIONS]
    assert Permission.INVENTORY_ADJUST not in ROLE_GRANTS[MerchantRole.GROWTH]
    assert Permission.FINANCE_EXPORT in ROLE_GRANTS[MerchantRole.FINANCE_VIEWER]
    assert Permission.CUSTOMER_DETAILS_READ not in ROLE_GRANTS[MerchantRole.FINANCE_VIEWER]
    assert Permission.TASKS_MANAGE not in ROLE_GRANTS[MerchantRole.VIEWER]


def test_admin_cannot_take_owner_only_actions():
    admin_permissions = ROLE_GRANTS[MerchantRole.ADMIN]
    assert Permission.MEMBERS_INVITE in admin_permissions
    assert Permission.MEMBERS_MANAGE in admin_permissions
    assert Permission.MEMBERS_ASSIGN_OWNER not in admin_permissions
    assert Permission.WORKSPACE_CLOSE not in admin_permissions
    assert Permission.BILLING_READ not in admin_permissions


def test_active_tenant_is_resolved_from_matching_server_membership():
    authority = resolve_tenant_authority(
        IDENTITY,
        "tenant-b",
        [membership("tenant-a", MerchantRole.OWNER), membership("tenant-b", MerchantRole.GROWTH)],
    )
    assert authority.tenant_id == "tenant-b"
    assert authority.role == MerchantRole.GROWTH


@pytest.mark.parametrize("status", [MembershipStatus.SUSPENDED, MembershipStatus.REVOKED])
def test_suspended_or_revoked_membership_has_no_access(status):
    with pytest.raises(AuthorizationDenied, match="Access denied"):
        resolve_tenant_authority(IDENTITY, "tenant-a", [membership("tenant-a", MerchantRole.OWNER, status=status)])


def test_claimed_tenant_without_membership_is_rejected_without_disclosure():
    with pytest.raises(AuthorizationDenied, match="Access denied for this workspace"):
        resolve_tenant_authority(IDENTITY, "tenant-b", [membership("tenant-a", MerchantRole.OWNER)])


def test_cross_tenant_object_id_is_hidden_even_for_owner():
    authority = resolve_tenant_authority(
        IDENTITY, "tenant-a", [membership("tenant-a", MerchantRole.OWNER)]
    )
    with pytest.raises(AuthorizationDenied, match="Resource not found"):
        require_permission(
            authority,
            Permission.INVENTORY_READ,
            resource_tenant_id="tenant-b",
        )


def test_growth_own_task_scope_rejects_another_users_task():
    authority = resolve_tenant_authority(
        IDENTITY, "tenant-a", [membership("tenant-a", MerchantRole.GROWTH)]
    )
    assert require_permission(
        authority,
        Permission.TASKS_MANAGE,
        resource_tenant_id="tenant-a",
        resource_owner_identity_id=IDENTITY_RECORD_ID,
    ) == GrantScope.OWN
    with pytest.raises(AuthorizationDenied, match="Resource not found"):
        require_permission(
            authority,
            Permission.TASKS_MANAGE,
            resource_tenant_id="tenant-a",
            resource_owner_identity_id="https://identity.example|user-2",
        )


def test_finance_viewer_cannot_reach_inventory_or_customer_details():
    authority = resolve_tenant_authority(
        IDENTITY, "tenant-a", [membership("tenant-a", MerchantRole.FINANCE_VIEWER)]
    )
    assert require_permission(authority, Permission.FINANCE_SUMMARY_READ) == GrantScope.ALL
    for denied in (Permission.INVENTORY_READ, Permission.CUSTOMER_DETAILS_READ):
        with pytest.raises(AuthorizationDenied, match="Permission denied"):
            require_permission(authority, denied)


def test_duplicate_active_memberships_fail_closed():
    duplicate = membership("tenant-a", MerchantRole.OWNER)
    with pytest.raises(AuthorizationDenied, match="Access denied"):
        resolve_tenant_authority(IDENTITY, "tenant-a", [duplicate, duplicate])


def test_platform_roles_are_separate_from_merchant_authority():
    assert set(PLATFORM_ROLE_GRANTS) == set(PlatformRole)
    support = PlatformAuthority(IDENTITY.identity_id, PlatformRole.SUPPORT)
    require_platform_permission(support, PlatformPermission.TENANT_METADATA_READ)
    with pytest.raises(AuthorizationDenied, match="Permission denied"):
        require_platform_permission(support, PlatformPermission.TENANT_SUSPEND)
    with pytest.raises(AuthorizationDenied, match="Permission denied"):
        require_permission(support, Permission.WORKSPACE_READ)  # type: ignore[arg-type]

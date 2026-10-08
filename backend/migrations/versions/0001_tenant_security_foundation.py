"""Create tenant, identity, membership, location, and audit foundations."""

from alembic import op
import sqlalchemy as sa


revision = "0001_tenant_security"
down_revision = None
branch_labels = None
depends_on = None


_TENANT_CONTEXT = """
tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
AND bizpilot_has_active_membership(
    NULLIF(current_setting('app.tenant_id', true), '')::uuid,
    NULLIF(current_setting('app.identity_id', true), '')::uuid,
    NULLIF(current_setting('app.membership_id', true), '')::uuid,
    NULLIF(current_setting('app.permission_version', true), '')::integer
)
"""

_TENANT_ROOT_CONTEXT = """
id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
AND bizpilot_has_active_membership(
    NULLIF(current_setting('app.tenant_id', true), '')::uuid,
    NULLIF(current_setting('app.identity_id', true), '')::uuid,
    NULLIF(current_setting('app.membership_id', true), '')::uuid,
    NULLIF(current_setting('app.permission_version', true), '')::integer
)
"""


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("slug", sa.String(80), nullable=False, unique=True),
        sa.Column("display_name", sa.String(160), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="Asia/Dhaka"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="BDT"),
        sa.Column("language", sa.String(16), nullable=False, server_default="bn"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("status IN ('active', 'suspended', 'closed')", name="ck_tenants_status"),
        sa.CheckConstraint("char_length(currency) = 3", name="ck_tenants_currency"),
    )
    op.create_table(
        "identities",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("issuer", sa.String(512), nullable=False),
        sa.Column("subject", sa.String(512), nullable=False),
        sa.Column("display_name", sa.String(160)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("issuer", "subject", name="uq_identities_issuer_subject"),
    )
    op.create_table(
        "memberships",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("identity_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("permission_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["identity_id"], ["identities.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "identity_id", name="uq_memberships_tenant_identity"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_memberships_tenant_id_id"),
        sa.CheckConstraint(
            "role IN ('owner', 'admin', 'operations', 'growth', 'finance_viewer', 'viewer')",
            name="ck_memberships_role",
        ),
        sa.CheckConstraint("status IN ('active', 'suspended', 'revoked')", name="ck_memberships_status"),
        sa.CheckConstraint("permission_version >= 1", name="ck_memberships_permission_version"),
    )
    op.create_index("ix_memberships_identity_tenant", "memberships", ["identity_id", "tenant_id"])
    op.create_table(
        "platform_staff",
        sa.Column("identity_id", sa.Uuid(), primary_key=True),
        sa.Column("role", sa.String(40), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["identity_id"], ["identities.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "role IN ('platform_owner', 'platform_operator', 'support_agent', 'security_responder')",
            name="ck_platform_staff_role",
        ),
        sa.CheckConstraint("status IN ('active', 'suspended', 'revoked')", name="ck_platform_staff_status"),
    )
    op.create_table(
        "locations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_locations_tenant_code"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_locations_tenant_id_id"),
    )
    op.create_index("ix_locations_tenant_name", "locations", ["tenant_id", "name"])
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("membership_id", sa.Uuid()),
        sa.Column("identity_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(120), nullable=False),
        sa.Column("target_type", sa.String(80), nullable=False),
        sa.Column("target_id", sa.String(160)),
        sa.Column("outcome", sa.String(40), nullable=False),
        sa.Column("correlation_id", sa.String(80), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["identity_id"], ["identities.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "membership_id"],
            ["memberships.tenant_id", "memberships.id"],
            name="fk_audit_membership_tenant",
            ondelete="RESTRICT",
        ),
    )
    op.create_index("ix_audit_events_tenant_time", "audit_events", ["tenant_id", "occurred_at"])

    op.execute("""
        CREATE OR REPLACE FUNCTION bizpilot_has_active_membership(
            requested_tenant uuid,
            requested_identity uuid,
            requested_membership uuid,
            requested_permission_version integer
        ) RETURNS boolean
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $$
            SELECT EXISTS (
                SELECT 1
                FROM public.memberships AS membership
                JOIN public.tenants AS tenant ON tenant.id = membership.tenant_id
                WHERE membership.id = requested_membership
                  AND membership.tenant_id = requested_tenant
                  AND membership.identity_id = requested_identity
                  AND membership.status = 'active'
                  AND membership.permission_version = requested_permission_version
                  AND tenant.status = 'active'
            )
        $$
    """)
    op.execute("REVOKE ALL ON FUNCTION bizpilot_has_active_membership(uuid, uuid, uuid, integer) FROM PUBLIC")
    op.execute("GRANT EXECUTE ON FUNCTION bizpilot_has_active_membership(uuid, uuid, uuid, integer) TO bizpilot_runtime")

    for table in ("tenants", "memberships", "locations", "audit_events"):
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
    # Membership and tenant roots remain owner-readable for the narrowly scoped
    # SECURITY DEFINER membership predicate. Runtime is never the table owner.
    for table in ("locations", "audit_events"):
        op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')

    op.execute(
        f"CREATE POLICY tenants_runtime_policy ON tenants TO bizpilot_runtime "
        f"USING ({_TENANT_ROOT_CONTEXT})"
    )
    op.execute(f"CREATE POLICY memberships_runtime_policy ON memberships TO bizpilot_runtime USING ({_TENANT_CONTEXT})")
    op.execute(
        f"CREATE POLICY locations_runtime_policy ON locations TO bizpilot_runtime "
        f"USING ({_TENANT_CONTEXT}) WITH CHECK ({_TENANT_CONTEXT})"
    )
    op.execute(
        f"CREATE POLICY audit_events_runtime_select ON audit_events FOR SELECT TO bizpilot_runtime "
        f"USING ({_TENANT_CONTEXT})"
    )
    op.execute(
        f"CREATE POLICY audit_events_runtime_insert ON audit_events FOR INSERT TO bizpilot_runtime "
        f"WITH CHECK ({_TENANT_CONTEXT})"
    )

    op.execute("GRANT SELECT ON tenants, memberships TO bizpilot_runtime")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON locations TO bizpilot_runtime")
    op.execute("GRANT SELECT, INSERT ON audit_events TO bizpilot_runtime")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS audit_events_runtime_insert ON audit_events")
    op.execute("DROP POLICY IF EXISTS audit_events_runtime_select ON audit_events")
    op.execute("DROP POLICY IF EXISTS locations_runtime_policy ON locations")
    op.execute("DROP POLICY IF EXISTS memberships_runtime_policy ON memberships")
    op.execute("DROP POLICY IF EXISTS tenants_runtime_policy ON tenants")
    op.execute("DROP FUNCTION IF EXISTS bizpilot_has_active_membership(uuid, uuid, uuid, integer)")
    op.drop_table("audit_events")
    op.drop_table("locations")
    op.drop_table("platform_staff")
    op.drop_index("ix_memberships_identity_tenant", table_name="memberships")
    op.drop_table("memberships")
    op.drop_table("identities")
    op.drop_table("tenants")

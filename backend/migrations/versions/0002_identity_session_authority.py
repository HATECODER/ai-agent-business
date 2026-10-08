"""Add identity revocation and restricted membership resolution."""

from alembic import op
import sqlalchemy as sa


revision = "0002_identity_authority"
down_revision = "0001_tenant_security"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "identities",
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
    )
    op.add_column(
        "identities",
        sa.Column("tokens_valid_after", sa.DateTime(timezone=True)),
    )
    op.create_check_constraint(
        "ck_identities_status",
        "identities",
        "status IN ('active', 'suspended', 'revoked')",
    )
    op.execute("""
        CREATE OR REPLACE FUNCTION bizpilot_resolve_membership(
            auth_issuer text,
            auth_subject text,
            selected_tenant uuid,
            token_issued_at timestamptz
        ) RETURNS TABLE (
            identity_id uuid,
            membership_id uuid,
            tenant_id uuid,
            role text,
            permission_version integer
        )
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $$
            SELECT
                identity.id,
                membership.id,
                membership.tenant_id,
                membership.role,
                membership.permission_version
            FROM public.identities AS identity
            JOIN public.memberships AS membership
              ON membership.identity_id = identity.id
            JOIN public.tenants AS tenant
              ON tenant.id = membership.tenant_id
            WHERE identity.issuer = auth_issuer
              AND identity.subject = auth_subject
              AND identity.status = 'active'
              AND (
                  identity.tokens_valid_after IS NULL
                  OR token_issued_at >= identity.tokens_valid_after
              )
              AND membership.tenant_id = selected_tenant
              AND membership.status = 'active'
              AND membership.permission_version >= 1
              AND tenant.status = 'active'
        $$
    """)
    op.execute(
        "REVOKE ALL ON FUNCTION "
        "bizpilot_resolve_membership(text, text, uuid, timestamptz) FROM PUBLIC"
    )
    op.execute(
        "GRANT EXECUTE ON FUNCTION "
        "bizpilot_resolve_membership(text, text, uuid, timestamptz) "
        "TO bizpilot_authenticator"
    )


def downgrade() -> None:
    op.execute(
        "DROP FUNCTION IF EXISTS "
        "bizpilot_resolve_membership(text, text, uuid, timestamptz)"
    )
    op.drop_constraint("ck_identities_status", "identities", type_="check")
    op.drop_column("identities", "tokens_valid_after")
    op.drop_column("identities", "status")

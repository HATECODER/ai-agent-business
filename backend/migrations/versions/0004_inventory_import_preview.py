"""Add tenant-isolated inventory import preview metadata."""

import sqlalchemy as sa
from alembic import op


revision = "0004_import_preview"
down_revision = "0003_inventory_read"
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


def upgrade() -> None:
    op.create_table(
        "inventory_import_previews",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("membership_id", sa.Uuid(), nullable=False),
        sa.Column("original_filename", sa.String(200), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("total_rows", sa.Integer(), nullable=False),
        sa.Column("valid_rows", sa.Integer(), nullable=False),
        sa.Column("error_rows", sa.Integer(), nullable=False),
        sa.Column("new_rows", sa.Integer(), nullable=False),
        sa.Column("change_rows", sa.Integer(), nullable=False),
        sa.Column("conflict_rows", sa.Integer(), nullable=False),
        sa.Column("unchanged_rows", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "membership_id"],
            ["memberships.tenant_id", "memberships.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("tenant_id", "id", name="uq_import_previews_tenant_id"),
        sa.CheckConstraint(
            "byte_size BETWEEN 1 AND 5242880", name="ck_import_preview_size"
        ),
        sa.CheckConstraint(
            "status IN ('ready', 'requires_review', 'needs_correction')",
            name="ck_import_preview_status",
        ),
        sa.CheckConstraint(
            "total_rows >= 0 AND valid_rows >= 0 AND error_rows >= 0 "
            "AND new_rows >= 0 AND change_rows >= 0 AND conflict_rows >= 0 "
            "AND unchanged_rows >= 0",
            name="ck_import_preview_counts_nonnegative",
        ),
        sa.CheckConstraint(
            "valid_rows + error_rows = total_rows",
            name="ck_import_preview_row_totals",
        ),
        sa.CheckConstraint(
            "new_rows + change_rows + conflict_rows + unchanged_rows = valid_rows",
            name="ck_import_preview_classification_totals",
        ),
        sa.CheckConstraint(
            "content_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_import_preview_sha256",
        ),
    )
    op.create_index(
        "ix_import_previews_tenant_created",
        "inventory_import_previews",
        ["tenant_id", "created_at"],
    )

    op.create_table(
        "inventory_import_errors",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("preview_id", sa.Uuid(), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("column_name", sa.String(64), nullable=False),
        sa.Column("error_code", sa.String(64), nullable=False),
        sa.Column("message", sa.String(240), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id", "preview_id"],
            ["inventory_import_previews.tenant_id", "inventory_import_previews.id"],
            ondelete="CASCADE",
        ),
        sa.CheckConstraint("row_number >= 1", name="ck_import_error_row_number"),
    )
    op.create_index(
        "ix_import_errors_tenant_preview",
        "inventory_import_errors",
        ["tenant_id", "preview_id", "row_number"],
    )

    for table in ("inventory_import_previews", "inventory_import_errors"):
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
        op.execute(
            f"CREATE POLICY {table}_runtime_select ON {table} "
            f"FOR SELECT TO bizpilot_runtime USING ({_TENANT_CONTEXT})"
        )
        op.execute(
            f"CREATE POLICY {table}_runtime_insert ON {table} "
            f"FOR INSERT TO bizpilot_runtime WITH CHECK ({_TENANT_CONTEXT})"
        )

    op.execute(
        "GRANT SELECT, INSERT ON inventory_import_previews, "
        "inventory_import_errors TO bizpilot_runtime"
    )


def downgrade() -> None:
    for table in ("inventory_import_errors", "inventory_import_previews"):
        op.execute(f"DROP POLICY IF EXISTS {table}_runtime_insert ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_runtime_select ON {table}")
        op.drop_table(table)

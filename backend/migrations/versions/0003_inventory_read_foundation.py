"""Add tenant-isolated product and inventory read foundations."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0003_inventory_read"
down_revision = "0002_identity_authority"
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
    op.add_column(
        "locations",
        sa.Column("source_kind", sa.String(24), nullable=False, server_default="manual"),
    )
    op.add_column("locations", sa.Column("source_reference", sa.String(160)))
    op.add_column("locations", sa.Column("source_version", sa.String(160)))
    op.add_column("locations", sa.Column("observed_at", sa.DateTime(timezone=True)))
    op.create_check_constraint(
        "ck_locations_source_kind",
        "locations",
        "source_kind IN ('manual', 'csv_snapshot')",
    )
    op.create_check_constraint(
        "ck_locations_csv_source",
        "locations",
        "source_kind <> 'csv_snapshot' OR source_reference IS NOT NULL",
    )

    op.create_table(
        "products",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("source_kind", sa.String(24), nullable=False),
        sa.Column("source_reference", sa.String(160)),
        sa.Column("source_version", sa.String(160)),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_products_tenant_id_id"),
        sa.CheckConstraint(
            "source_kind IN ('manual', 'csv_snapshot')",
            name="ck_products_source_kind",
        ),
        sa.CheckConstraint(
            "source_kind <> 'csv_snapshot' OR source_reference IS NOT NULL",
            name="ck_products_csv_source",
        ),
        sa.CheckConstraint("char_length(trim(name)) > 0", name="ck_products_name"),
    )
    op.create_index("ix_products_tenant_name", "products", ["tenant_id", "name"])

    op.create_table(
        "product_variants",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("sku", sa.String(120), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column(
            "options",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("base_price_minor", sa.BigInteger()),
        sa.Column("currency", sa.String(3)),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("source_kind", sa.String(24), nullable=False),
        sa.Column("source_reference", sa.String(160)),
        sa.Column("source_version", sa.String(160)),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "product_id"],
            ["products.tenant_id", "products.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("tenant_id", "id", name="uq_variants_tenant_id_id"),
        sa.UniqueConstraint("tenant_id", "sku", name="uq_variants_tenant_sku"),
        sa.CheckConstraint(
            "source_kind IN ('manual', 'csv_snapshot')",
            name="ck_variants_source_kind",
        ),
        sa.CheckConstraint(
            "source_kind <> 'csv_snapshot' OR source_reference IS NOT NULL",
            name="ck_variants_csv_source",
        ),
        sa.CheckConstraint("char_length(trim(sku)) > 0", name="ck_variants_sku"),
        sa.CheckConstraint("char_length(trim(name)) > 0", name="ck_variants_name"),
        sa.CheckConstraint(
            "(base_price_minor IS NULL AND currency IS NULL) OR "
            "(base_price_minor >= 0 AND char_length(currency) = 3)",
            name="ck_variants_price",
        ),
    )
    op.create_index(
        "ix_variants_tenant_product",
        "product_variants",
        ["tenant_id", "product_id"],
    )

    op.create_table(
        "inventory_balances",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("variant_id", sa.Uuid(), nullable=False),
        sa.Column("location_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.BigInteger(), nullable=False),
        sa.Column("low_stock_threshold", sa.BigInteger(), nullable=False),
        sa.Column("record_version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("source_kind", sa.String(24), nullable=False),
        sa.Column("source_reference", sa.String(160)),
        sa.Column("source_version", sa.String(160)),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "variant_id"],
            ["product_variants.tenant_id", "product_variants.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "location_id"],
            ["locations.tenant_id", "locations.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("tenant_id", "id", name="uq_balances_tenant_id_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "id",
            "variant_id",
            "location_id",
            name="uq_balances_tenant_identity_location",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "variant_id",
            "location_id",
            name="uq_balances_tenant_variant_location",
        ),
        sa.CheckConstraint("quantity >= 0", name="ck_balances_quantity"),
        sa.CheckConstraint(
            "low_stock_threshold >= 0",
            name="ck_balances_low_stock_threshold",
        ),
        sa.CheckConstraint("record_version >= 1", name="ck_balances_record_version"),
        sa.CheckConstraint(
            "source_kind IN ('manual', 'csv_snapshot')",
            name="ck_balances_source_kind",
        ),
        sa.CheckConstraint(
            "source_kind <> 'csv_snapshot' OR source_reference IS NOT NULL",
            name="ck_balances_csv_source",
        ),
    )
    op.create_index(
        "ix_balances_tenant_location",
        "inventory_balances",
        ["tenant_id", "location_id"],
    )
    op.create_index(
        "ix_balances_tenant_low_stock",
        "inventory_balances",
        ["tenant_id", "quantity", "low_stock_threshold"],
    )

    op.create_table(
        "inventory_movements",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("balance_id", sa.Uuid(), nullable=False),
        sa.Column("variant_id", sa.Uuid(), nullable=False),
        sa.Column("location_id", sa.Uuid(), nullable=False),
        sa.Column("actor_type", sa.String(16), nullable=False),
        sa.Column("membership_id", sa.Uuid()),
        sa.Column("quantity_before", sa.BigInteger(), nullable=False),
        sa.Column("quantity_delta", sa.BigInteger(), nullable=False),
        sa.Column("quantity_after", sa.BigInteger(), nullable=False),
        sa.Column("reason", sa.String(200), nullable=False),
        sa.Column("source_kind", sa.String(24), nullable=False),
        sa.Column("source_reference", sa.String(160)),
        sa.Column("source_version", sa.String(160)),
        sa.Column("idempotency_key", sa.String(160), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "balance_id", "variant_id", "location_id"],
            [
                "inventory_balances.tenant_id",
                "inventory_balances.id",
                "inventory_balances.variant_id",
                "inventory_balances.location_id",
            ],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "membership_id"],
            ["memberships.tenant_id", "memberships.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("tenant_id", "id", name="uq_movements_tenant_id_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "idempotency_key",
            name="uq_movements_tenant_idempotency",
        ),
        sa.CheckConstraint("quantity_before >= 0", name="ck_movements_before"),
        sa.CheckConstraint("quantity_after >= 0", name="ck_movements_after"),
        sa.CheckConstraint("quantity_delta <> 0", name="ck_movements_delta"),
        sa.CheckConstraint(
            "quantity_after = quantity_before + quantity_delta",
            name="ck_movements_arithmetic",
        ),
        sa.CheckConstraint(
            "source_kind IN ('manual', 'csv_snapshot')",
            name="ck_movements_source_kind",
        ),
        sa.CheckConstraint(
            "source_kind <> 'csv_snapshot' OR source_reference IS NOT NULL",
            name="ck_movements_csv_source",
        ),
        sa.CheckConstraint(
            "(actor_type = 'member' AND membership_id IS NOT NULL) OR "
            "(actor_type = 'system' AND membership_id IS NULL)",
            name="ck_movements_actor",
        ),
        sa.CheckConstraint("char_length(trim(reason)) > 0", name="ck_movements_reason"),
        sa.CheckConstraint(
            "char_length(trim(idempotency_key)) > 0",
            name="ck_movements_idempotency",
        ),
    )
    op.create_index(
        "ix_movements_tenant_balance_time",
        "inventory_movements",
        ["tenant_id", "balance_id", "occurred_at"],
    )

    for table in (
        "products",
        "product_variants",
        "inventory_balances",
        "inventory_movements",
    ):
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
        op.execute(
            f"CREATE POLICY {table}_runtime_select ON {table} "
            f"FOR SELECT TO bizpilot_runtime USING ({_TENANT_CONTEXT})"
        )

    op.execute(
        "GRANT SELECT ON products, product_variants, inventory_balances, "
        "inventory_movements TO bizpilot_runtime"
    )
    op.execute("REVOKE INSERT, UPDATE, DELETE ON locations FROM bizpilot_runtime")


def downgrade() -> None:
    op.execute("GRANT INSERT, UPDATE, DELETE ON locations TO bizpilot_runtime")
    for table in (
        "inventory_movements",
        "inventory_balances",
        "product_variants",
        "products",
    ):
        op.execute(f"DROP POLICY IF EXISTS {table}_runtime_select ON {table}")
        op.drop_table(table)
    op.drop_constraint("ck_locations_csv_source", "locations", type_="check")
    op.drop_constraint("ck_locations_source_kind", "locations", type_="check")
    op.drop_column("locations", "observed_at")
    op.drop_column("locations", "source_version")
    op.drop_column("locations", "source_reference")
    op.drop_column("locations", "source_kind")

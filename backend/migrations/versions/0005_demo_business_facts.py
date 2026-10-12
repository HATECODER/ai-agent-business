"""Add tenant-isolated November demo business fact tables."""

import sqlalchemy as sa
from alembic import op

revision = "0005_demo_facts"
down_revision = "0004_import_preview"
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


def _source_columns() -> tuple[sa.Column, ...]:
    return (
        sa.Column("source_reference", sa.String(160), nullable=False),
        sa.Column("source_version", sa.String(160), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
    )


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("customer_key", sa.String(120), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        *_source_columns(),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_customers_tenant_id_id"),
        sa.UniqueConstraint("tenant_id", "customer_key", name="uq_customers_tenant_key"),
        sa.CheckConstraint("char_length(trim(customer_key)) > 0", name="ck_customers_key"),
    )
    op.create_table(
        "orders",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("order_key", sa.String(120), nullable=False),
        sa.Column("order_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("total_amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("amount_received_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="BDT"),
        *_source_columns(),
        sa.ForeignKeyConstraint(
            ["tenant_id", "customer_id"],
            ["customers.tenant_id", "customers.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("tenant_id", "order_key", name="uq_orders_tenant_key"),
        sa.CheckConstraint(
            "status IN ('pending', 'confirmed', 'delivered', 'cancelled')",
            name="ck_orders_status",
        ),
        sa.CheckConstraint(
            "total_amount_minor >= 0 AND amount_received_minor >= 0 "
            "AND amount_received_minor <= total_amount_minor",
            name="ck_orders_amounts",
        ),
    )
    op.create_table(
        "expenses",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("expense_key", sa.String(120), nullable=False),
        sa.Column("expense_date", sa.Date(), nullable=False),
        sa.Column("category", sa.String(80), nullable=False),
        sa.Column("description", sa.String(240), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="BDT"),
        *_source_columns(),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "expense_key", name="uq_expenses_tenant_key"),
        sa.CheckConstraint("amount_minor >= 0", name="ck_expenses_amount"),
    )
    op.create_table(
        "tasks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("task_key", sa.String(120), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("priority", sa.String(16), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        *_source_columns(),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "task_key", name="uq_tasks_tenant_key"),
        sa.CheckConstraint(
            "priority IN ('critical', 'high', 'medium', 'low')",
            name="ck_tasks_priority",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'in_progress', 'completed')",
            name="ck_tasks_status",
        ),
    )

    for table in ("customers", "orders", "expenses", "tasks"):
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
        op.execute(
            f"CREATE POLICY {table}_runtime_select ON {table} "
            f"FOR SELECT TO bizpilot_runtime USING ({_TENANT_CONTEXT})"
        )
    op.execute("GRANT SELECT ON customers, orders, expenses, tasks TO bizpilot_runtime")


def downgrade() -> None:
    for table in ("tasks", "expenses", "orders", "customers"):
        op.execute(f"DROP POLICY IF EXISTS {table}_runtime_select ON {table}")
        op.drop_table(table)

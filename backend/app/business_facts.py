"""Deterministic tenant-scoped facts for the November merchant demonstration."""

from collections.abc import Callable
from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError

from backend.app.authorization import Permission, TenantAuthority, require_permission
from backend.app.database import tenant_transaction


class BusinessFactsUnavailable(RuntimeError):
    """Business facts could not be read without exposing infrastructure details."""


class FinanceSummary(BaseModel):
    reference_date: date
    order_count: int = Field(ge=0)
    revenue_bdt: int = Field(ge=0)
    receipts_bdt: int = Field(ge=0)
    receivable_bdt: int = Field(ge=0)
    average_order_value_bdt: float = Field(ge=0)
    expenses_bdt: int = Field(ge=0)
    receipts_less_expenses_bdt: int


class InactiveCustomerSummary(BaseModel):
    reference_date: date
    inactive_days: int = Field(ge=1, le=365)
    inactive_customer_keys: list[str]


class AttentionTask(BaseModel):
    task_key: str
    title: str
    category: str
    priority: str
    status: str


class AttentionTaskSummary(BaseModel):
    tasks: list[AttentionTask]


FinanceReader = Callable[[TenantAuthority, date], FinanceSummary]
InactiveCustomerReader = Callable[[TenantAuthority, date, int], InactiveCustomerSummary]
TaskReader = Callable[[TenantAuthority], AttentionTaskSummary]


def database_finance_reader(engine: Engine) -> FinanceReader:
    def read(authority: TenantAuthority, reference_date: date) -> FinanceSummary:
        require_permission(authority, Permission.FINANCE_SUMMARY_READ)
        try:
            with tenant_transaction(engine, authority) as connection:
                row = connection.execute(
                    text("""
                        WITH sales AS (
                            SELECT COUNT(*) AS order_count,
                                   COALESCE(SUM(total_amount_minor), 0) AS revenue,
                                   COALESCE(SUM(amount_received_minor), 0) AS receipts
                            FROM orders
                            WHERE tenant_id = :tenant_id AND order_date = :reference_date
                              AND status IN ('confirmed', 'delivered')
                        ), dated_expenses AS (
                            SELECT COALESCE(SUM(amount_minor), 0) AS expenses
                            FROM expenses
                            WHERE tenant_id = :tenant_id AND expense_date = :reference_date
                        )
                        SELECT order_count, revenue, receipts, expenses FROM sales, dated_expenses
                    """),
                    {"tenant_id": UUID(authority.tenant_id), "reference_date": reference_date},
                ).mappings().one()
        except (SQLAlchemyError, ValueError) as error:
            raise BusinessFactsUnavailable("Finance summary unavailable.") from error
        revenue = int(row["revenue"]) // 100
        receipts = int(row["receipts"]) // 100
        expenses = int(row["expenses"]) // 100
        count = int(row["order_count"])
        return FinanceSummary(
            reference_date=reference_date,
            order_count=count,
            revenue_bdt=revenue,
            receipts_bdt=receipts,
            receivable_bdt=revenue - receipts,
            average_order_value_bdt=round(revenue / count, 2) if count else 0,
            expenses_bdt=expenses,
            receipts_less_expenses_bdt=receipts - expenses,
        )

    return read


def database_inactive_customer_reader(engine: Engine) -> InactiveCustomerReader:
    def read(
        authority: TenantAuthority, reference_date: date, inactive_days: int
    ) -> InactiveCustomerSummary:
        require_permission(authority, Permission.CUSTOMER_SEGMENTS_READ)
        if not 1 <= inactive_days <= 365:
            raise ValueError("Inactive window is invalid.")
        try:
            with tenant_transaction(engine, authority) as connection:
                rows = connection.execute(
                    text("""
                        SELECT customer.customer_key
                        FROM customers AS customer
                        LEFT JOIN orders AS customer_order
                          ON customer_order.tenant_id = customer.tenant_id
                         AND customer_order.customer_id = customer.id
                         AND customer_order.status = 'delivered'
                        WHERE customer.tenant_id = :tenant_id
                        GROUP BY customer.id, customer.customer_key
                        HAVING MAX(customer_order.order_date) IS NULL
                           OR MAX(customer_order.order_date) <
                              :reference_date - CAST(:inactive_days AS integer)
                        ORDER BY customer.customer_key
                    """),
                    {
                        "tenant_id": UUID(authority.tenant_id),
                        "reference_date": reference_date,
                        "inactive_days": inactive_days,
                    },
                ).mappings().all()
        except (SQLAlchemyError, ValueError) as error:
            raise BusinessFactsUnavailable("Customer segment unavailable.") from error
        return InactiveCustomerSummary(
            reference_date=reference_date,
            inactive_days=inactive_days,
            inactive_customer_keys=[str(row["customer_key"]) for row in rows],
        )

    return read


def database_attention_task_reader(engine: Engine) -> TaskReader:
    def read(authority: TenantAuthority) -> AttentionTaskSummary:
        require_permission(authority, Permission.TASKS_READ)
        try:
            with tenant_transaction(engine, authority) as connection:
                rows = connection.execute(
                    text("""
                        SELECT task_key, title, category, priority, status
                        FROM tasks
                        WHERE tenant_id = :tenant_id
                          AND status IN ('pending', 'in_progress')
                        ORDER BY CASE priority
                            WHEN 'critical' THEN 0 WHEN 'high' THEN 1
                            WHEN 'medium' THEN 2 ELSE 3 END, task_key
                    """),
                    {"tenant_id": UUID(authority.tenant_id)},
                ).mappings().all()
        except (SQLAlchemyError, ValueError) as error:
            raise BusinessFactsUnavailable("Task summary unavailable.") from error
        return AttentionTaskSummary(tasks=[AttentionTask.model_validate(dict(row)) for row in rows])

    return read

from datetime import date

import pytest

from backend.app.authorization import AuthorizationDenied, MerchantRole, TenantAuthority
from backend.app.business_facts import (
    database_attention_task_reader,
    database_finance_reader,
    database_inactive_customer_reader,
)

TENANT_ID = "10000000-0000-0000-0000-000000000001"


def authority(role: MerchantRole = MerchantRole.OWNER) -> TenantAuthority:
    return TenantAuthority(
        identity_id="10000000-0000-0000-0000-000000000002",
        membership_id="10000000-0000-0000-0000-000000000003",
        tenant_id=TENANT_ID,
        role=role,
        permission_version=1,
    )


class Result:
    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        return self

    def one(self):
        return self.rows[0]

    def all(self):
        return self.rows


class Connection:
    def __init__(self):
        self.calls = []

    def execute(self, statement, parameters=None):
        sql = str(statement)
        self.calls.append((sql, parameters or {}))
        if "SET LOCAL ROLE" in sql or "set_config" in sql:
            return Result([])
        if "WITH sales" in sql:
            return Result([{"order_count": 2, "revenue": 500000, "receipts": 350000, "expenses": 80000}])
        if "MAX(customer_order.order_date)" in sql:
            return Result([{"customer_key": key} for key in ("CUST-002", "CUST-004", "CUST-005")])
        if "FROM tasks" in sql:
            return Result([
                {"task_key": "TASK-001", "title": "Confirm dispatch list", "category": "operations", "priority": "high", "status": "pending"},
                {"task_key": "TASK-002", "title": "Review outstanding receivables", "category": "finance", "priority": "high", "status": "in_progress"},
            ])
        raise AssertionError("Unexpected SQL")


class Transaction:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self.connection

    def __exit__(self, *_args):
        return False


class Engine:
    def __init__(self):
        self.connection = Connection()

    def begin(self):
        return Transaction(self.connection)


def test_finance_summary_matches_reviewed_fixture_values():
    result = database_finance_reader(Engine())(authority(), date(2026, 11, 1))
    assert result.model_dump() == {
        "reference_date": date(2026, 11, 1),
        "order_count": 2,
        "revenue_bdt": 5000,
        "receipts_bdt": 3500,
        "receivable_bdt": 1500,
        "average_order_value_bdt": 2500.0,
        "expenses_bdt": 800,
        "receipts_less_expenses_bdt": 2700,
    }


def test_inactive_customer_summary_returns_only_pseudonymous_keys():
    result = database_inactive_customer_reader(Engine())(
        authority(MerchantRole.GROWTH), date(2026, 11, 1), 30
    )
    assert result.inactive_customer_keys == ["CUST-002", "CUST-004", "CUST-005"]
    assert "display_name" not in result.model_dump_json()


def test_attention_tasks_are_read_only_business_fields():
    result = database_attention_task_reader(Engine())(authority(MerchantRole.VIEWER))
    assert [task.task_key for task in result.tasks] == ["TASK-001", "TASK-002"]
    assert "tenant_id" not in result.model_dump_json()


@pytest.mark.parametrize(
    ("reader", "role", "arguments"),
    [
        (database_finance_reader, MerchantRole.OPERATIONS, (date(2026, 11, 1),)),
        (database_inactive_customer_reader, MerchantRole.VIEWER, (date(2026, 11, 1), 30)),
    ],
)
def test_domain_permissions_are_checked_before_database_access(reader, role, arguments):
    class NoDatabase:
        def begin(self):
            raise AssertionError("database must not be reached")

    with pytest.raises(AuthorizationDenied):
        reader(NoDatabase())(authority(role), *arguments)

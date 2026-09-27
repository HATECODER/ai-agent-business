from datetime import timedelta

import pytest

from database.db import connect
from database.seed import today
from tools.finance import get_expense_summary, get_financial_summary, get_sales_summary


def test_finance_matches_independent_sql_totals(seeded_db):
    day = today().date().isoformat()
    with connect(seeded_db) as db:
        gross, received, count = db.execute("""SELECT SUM(total_amount), SUM(amount_received), COUNT(*)
            FROM orders WHERE order_date = ? AND status IN ('confirmed', 'delivered')""", (day,)).fetchone()
        expenses = db.execute("SELECT SUM(amount) FROM expenses WHERE expense_date = ?", (day,)).fetchone()[0]
    sales = get_sales_summary(db_path=seeded_db)
    expense_summary = get_expense_summary(db_path=seeded_db)
    summary = get_financial_summary(db_path=seeded_db)
    assert sales["order_count"] == count
    assert sales["gross_sales"] == gross
    assert sales["amount_received"] == received
    assert sales["pending_receivable"] == gross - received
    assert sales["average_order_value"] == round(gross / count, 2)
    assert expense_summary["expenses"] == expenses
    assert summary["net_cash_flow"] == received - expenses
    assert summary["receivable"] == gross - received


def test_empty_date_range_and_invalid_range(seeded_db):
    future = (today().date() + timedelta(days=366)).isoformat()
    result = get_financial_summary(future, future, seeded_db)
    assert result["revenue"] == result["expenses"] == result["net_cash_flow"] == 0
    with pytest.raises(ValueError):
        get_sales_summary(future, today().date().isoformat(), seeded_db)

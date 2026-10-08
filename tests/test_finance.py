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
    assert sales["order_cohort_receipts"] == received
    assert sales["order_cohort_receivable"] == gross - received
    assert sales["average_order_value"] == round(gross / count, 2)
    assert expense_summary["expenses"] == expenses
    assert summary["order_cohort_receipts_less_dated_expenses"] == received - expenses
    assert summary["order_cohort_receivable"] == gross - received
    assert summary["cash_flow_available"] is False


def test_empty_date_range_and_invalid_range(seeded_db):
    future = (today().date() + timedelta(days=366)).isoformat()
    result = get_financial_summary(future, future, seeded_db)
    assert result["revenue"] == result["dated_expenses"] == 0
    assert result["order_cohort_receipts_less_dated_expenses"] == 0
    with pytest.raises(ValueError):
        get_sales_summary(future, today().date().isoformat(), seeded_db)


def test_older_order_receipt_is_not_claimed_as_todays_cash_flow(seeded_db):
    today_string = today().date().isoformat()
    older_day = (today().date() - timedelta(days=2)).isoformat()
    before = get_financial_summary(db_path=seeded_db)
    with connect(seeded_db) as db:
        db.execute("""INSERT INTO orders
            (id, customer_id, order_date, status, total_amount, payment_status,
             amount_received, created_at) VALUES (999, 1, ?, 'delivered', 1000,
             'partial', 777, ?)""", (older_day, today_string))
    after = get_financial_summary(db_path=seeded_db)
    assert after["order_cohort_receipts"] == before["order_cohort_receipts"]
    assert after["cash_flow_available"] is False
    assert "Payment dates" in after["metric_note"]


def test_business_date_uses_bangladesh_offset():
    assert today().utcoffset() == timedelta(hours=6)

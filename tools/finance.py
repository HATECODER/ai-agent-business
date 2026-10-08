"""All monetary figures are calculated in SQL/Python as whole BDT."""

from datetime import date
from pathlib import Path

from database.db import connect
from database.seed import today


SALES_STATUSES = ("confirmed", "delivered")


def _date_range(start_date: str | None, end_date: str | None) -> tuple[str, str]:
    start = date.fromisoformat(start_date) if start_date else today().date()
    end = date.fromisoformat(end_date) if end_date else start
    if end < start:
        raise ValueError("End date must not be before start date.")
    return start.isoformat(), end.isoformat()


def get_sales_summary(start_date: str | None = None, end_date: str | None = None,
                      db_path: str | Path | None = None) -> dict:
    start, end = _date_range(start_date, end_date)
    with connect(db_path) as db:
        row = db.execute("""SELECT COUNT(*) AS order_count,
            COALESCE(SUM(total_amount), 0) AS gross_sales,
            COALESCE(SUM(amount_received), 0) AS amount_received
            FROM orders WHERE status IN ('confirmed', 'delivered')
            AND order_date BETWEEN ? AND ?""", (start, end)).fetchone()
    count, gross, received = row["order_count"], row["gross_sales"], row["amount_received"]
    return {"start_date": start, "end_date": end, "order_count": count,
            "gross_sales": gross, "order_cohort_receipts": received,
            "order_cohort_receivable": gross - received,
            "average_order_value": round(gross / count, 2) if count else 0,
            "currency": "BDT", "sales_statuses": list(SALES_STATUSES),
            "metric_note": ("Receipts and receivables are for orders dated in this range. "
                            "Payment-event dates and the full outstanding balance are not modeled.")}


def get_expense_summary(start_date: str | None = None, end_date: str | None = None,
                        db_path: str | Path | None = None) -> dict:
    start, end = _date_range(start_date, end_date)
    with connect(db_path) as db:
        row = db.execute("""SELECT COUNT(*) AS expense_count,
            COALESCE(SUM(amount), 0) AS expenses FROM expenses
            WHERE expense_date BETWEEN ? AND ?""", (start, end)).fetchone()
    return {"start_date": start, "end_date": end, "expense_count": row["expense_count"],
            "expenses": row["expenses"], "currency": "BDT"}


def get_financial_summary(start_date: str | None = None, end_date: str | None = None,
                          db_path: str | Path | None = None) -> dict:
    sales = get_sales_summary(start_date, end_date, db_path)
    expenses = get_expense_summary(start_date, end_date, db_path)
    return {"start_date": sales["start_date"], "end_date": sales["end_date"],
            "revenue": sales["gross_sales"],
            "order_cohort_receipts": sales["order_cohort_receipts"],
            "dated_expenses": expenses["expenses"],
            "order_cohort_receipts_less_dated_expenses": (
                sales["order_cohort_receipts"] - expenses["expenses"]),
            "order_cohort_receivable": sales["order_cohort_receivable"],
            "order_count": sales["order_count"],
            "average_order_value": sales["average_order_value"], "currency": "BDT",
            "sales_statuses": list(SALES_STATUSES),
            "cash_flow_available": False,
            "metric_note": ("This is an order-cohort operating view, not cash flow. Payment dates, "
                            "opening balance, refunds, settlement fees, and a full receivables ledger "
                            "are not modeled.")}

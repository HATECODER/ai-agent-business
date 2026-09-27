"""Gather verified business facts for the owner's daily brief."""

from pathlib import Path
from tools.finance import get_financial_summary
from tools.growth import get_inactive_customers
from tools.operations import get_low_stock_products, get_pending_tasks


def get_business_summary(db_path: str | Path | None = None) -> dict:
    inactive = get_inactive_customers(30, db_path)
    pending = get_pending_tasks(db_path=db_path)
    return {
        "low_stock_items": get_low_stock_products(db_path),
        "high_priority_tasks": [task for task in pending if task["priority"] in ("high", "critical")],
        "inactive_customer_count": len(inactive),
        "inactive_customers": inactive,
        "financial_summary": get_financial_summary(db_path=db_path),
    }

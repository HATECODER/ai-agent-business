"""Validate the November demo fixture pack and its expected business results."""

from __future__ import annotations

import csv
import json
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.inventory_import import validate_inventory_csv

DEFAULT_FIXTURE_DIR = PROJECT_ROOT / "demo_fixtures" / "november_v1"
SALES_STATUSES = {"confirmed", "delivered"}
OPEN_TASK_STATUSES = {"pending", "in_progress"}
PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _inventory_results(rows: list[dict[str, str]], multiplier: int) -> dict:
    keys = [(row["sku"], row["location_code"]) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("Inventory fixture contains duplicate SKU/location keys.")
    low = [
        row
        for row in rows
        if int(row["quantity"]) <= int(row["low_stock_threshold"])
    ]
    return {
        "variants": len(rows),
        "normal_stock": len(rows) - len(low),
        "low_stock_including_out_of_stock": len(low),
        "out_of_stock": sum(int(row["quantity"]) == 0 for row in rows),
        "low_stock_skus": [row["sku"] for row in low],
        "total_suggested_restock_units": sum(
            max(
                0,
                multiplier * int(row["low_stock_threshold"])
                - int(row["quantity"]),
            )
            for row in low
        ),
    }


def _finance_results(
    orders: list[dict[str, str]],
    expenses: list[dict[str, str]],
    reference_date: str,
) -> dict:
    included = [
        row
        for row in orders
        if row["order_date"] == reference_date and row["status"] in SALES_STATUSES
    ]
    revenue = sum(int(row["total_amount_bdt"]) for row in included)
    receipts = sum(int(row["amount_received_bdt"]) for row in included)
    dated_expenses = sum(
        int(row["amount_bdt"])
        for row in expenses
        if row["expense_date"] == reference_date
    )
    return {
        "order_count": len(included),
        "revenue_bdt": revenue,
        "order_cohort_receipts_bdt": receipts,
        "order_cohort_receivable_bdt": revenue - receipts,
        "average_order_value_bdt": round(revenue / len(included), 2)
        if included
        else 0,
        "dated_expenses_bdt": dated_expenses,
        "receipts_less_dated_expenses_bdt": receipts - dated_expenses,
    }


def _customer_results(
    customers: list[dict[str, str]],
    orders: list[dict[str, str]],
    reference_date: str,
    inactive_days: int,
) -> dict:
    cutoff = date.fromisoformat(reference_date) - timedelta(days=inactive_days)
    last_delivered: dict[str, date] = {}
    for row in orders:
        if row["status"] != "delivered":
            continue
        customer_key = row["customer_key"]
        order_date = date.fromisoformat(row["order_date"])
        if order_date > last_delivered.get(customer_key, date.min):
            last_delivered[customer_key] = order_date
    inactive = [
        row["customer_key"]
        for row in customers
        if last_delivered.get(row["customer_key"]) is None
        or last_delivered[row["customer_key"]] < cutoff
    ]
    return {
        "inactive_cutoff_exclusive": cutoff.isoformat(),
        "inactive_count": len(inactive),
        "inactive_customer_keys": inactive,
    }


def _task_results(tasks: list[dict[str, str]]) -> dict:
    attention = [row for row in tasks if row["status"] in OPEN_TASK_STATUSES]
    attention.sort(key=lambda row: (PRIORITY_ORDER[row["priority"]], row["task_key"]))
    return {
        "attention_count": len(attention),
        "ordered_task_keys": [row["task_key"] for row in attention],
    }


def _preview_results(fixture_dir: Path, inventory: list[dict[str, str]]) -> dict:
    existing = {
        (row["sku"], row["location_code"]): row for row in inventory
    }
    results: dict[str, dict[str, int]] = {}
    for filename in (
        "preview-valid.csv",
        "preview-conflict.csv",
        "preview-invalid.csv",
    ):
        content = (fixture_dir / filename).read_bytes()
        _, parsed = validate_inventory_csv(filename, "text/csv", content)
        counts = {
            "new": 0,
            "changed": 0,
            "errors": parsed.total_rows - len(parsed.rows),
            "conflicts": 0,
        }
        for row in parsed.rows:
            current = existing.get((row.sku, row.location_code))
            if current is None:
                counts["new"] += 1
            elif (
                row.expected_record_version is not None
                and row.expected_record_version
                != int(current["expected_record_version"])
            ):
                counts["conflicts"] += 1
            else:
                base_price_minor = (
                    int(Decimal(current["base_price_bdt"]) * 100)
                    if current["base_price_bdt"]
                    else None
                )
                current_values = (
                    current["product_name"],
                    current["variant_name"],
                    current["location_name"],
                    int(current["quantity"]),
                    int(current["low_stock_threshold"]),
                    json.loads(current["variant_options"] or "{}"),
                    base_price_minor,
                )
                incoming_values = (
                    row.product_name,
                    row.variant_name,
                    row.location_name,
                    row.quantity,
                    row.low_stock_threshold,
                    row.variant_options,
                    row.base_price_minor,
                )
                if incoming_values != current_values:
                    counts["changed"] += 1
        results[filename] = counts
    return results


def calculate_results(fixture_dir: Path = DEFAULT_FIXTURE_DIR) -> dict:
    manifest = json.loads((fixture_dir / "manifest.json").read_text(encoding="utf-8"))
    inventory = _csv_rows(fixture_dir / "inventory.csv")
    orders = _csv_rows(fixture_dir / "orders.csv")
    customers = _csv_rows(fixture_dir / "customers.csv")
    expenses = _csv_rows(fixture_dir / "expenses.csv")
    tasks = _csv_rows(fixture_dir / "tasks.csv")
    reference_date = manifest["reference_date"]
    return {
        "inventory": _inventory_results(
            inventory, manifest["restock_target_threshold_multiplier"]
        ),
        "finance_on_reference_date": _finance_results(
            orders, expenses, reference_date
        ),
        "customers": _customer_results(
            customers, orders, reference_date, manifest["inactive_days"]
        ),
        "tasks": _task_results(tasks),
        "preview_cases": _preview_results(fixture_dir, inventory),
    }


def validate_fixture_pack(fixture_dir: Path = DEFAULT_FIXTURE_DIR) -> list[str]:
    expected = json.loads(
        (fixture_dir / "expected-results.json").read_text(encoding="utf-8")
    )
    actual = calculate_results(fixture_dir)
    return [] if actual == expected else [
        "Calculated fixture results do not match expected-results.json.",
        f"Expected: {json.dumps(expected, sort_keys=True)}",
        f"Actual: {json.dumps(actual, sort_keys=True)}",
    ]


if __name__ == "__main__":
    failures = validate_fixture_pack()
    if failures:
        raise SystemExit("\n".join(failures))
    print("November demo fixture pack is valid and expected results match.")

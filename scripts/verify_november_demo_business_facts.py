"""Verify Day 8 facts through restricted auth and runtime database roles."""

from __future__ import annotations

import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.business_facts import (
    database_attention_task_reader,
    database_finance_reader,
    database_inactive_customer_reader,
)
from backend.app.database import create_database_engine
from backend.app.identity import VerifiedIdentity
from backend.app.memberships import (
    create_auth_engine,
    persistent_authority_resolver,
)

ENV_PATH = ROOT / ".env"


def main() -> int:
    values = dotenv_values(ENV_PATH)
    required = (
        "BIZPILOT_DATABASE_URL",
        "BIZPILOT_AUTH_DATABASE_URL",
        "BIZPILOT_OIDC_ISSUER",
        "BIZPILOT_STAGING_OWNER_SUBJECT",
        "BIZPILOT_WORKSPACE_ID",
    )
    if any(not (values.get(key) or "").strip() for key in required):
        print("Restricted Day 8 verification configuration is incomplete.")
        return 1

    runtime_engine = create_database_engine(values["BIZPILOT_DATABASE_URL"])
    auth_engine = create_auth_engine(values["BIZPILOT_AUTH_DATABASE_URL"])
    try:
        now = datetime.now(timezone.utc)
        identity = VerifiedIdentity(
            values["BIZPILOT_OIDC_ISSUER"],
            values["BIZPILOT_STAGING_OWNER_SUBJECT"],
            now,
            now + timedelta(minutes=5),
        )
        authority = persistent_authority_resolver(auth_engine)(
            identity, values["BIZPILOT_WORKSPACE_ID"]
        )
        reference_date = date(2026, 11, 1)
        finance = database_finance_reader(runtime_engine)(authority, reference_date)
        inactive = database_inactive_customer_reader(runtime_engine)(
            authority, reference_date, 30
        )
        tasks = database_attention_task_reader(runtime_engine)(authority)
        result = {
            "finance": finance.model_dump(mode="json"),
            "inactive_customer_keys": inactive.inactive_customer_keys,
            "attention_task_keys": [task.task_key for task in tasks.tasks],
        }
        expected = {
            "finance": {
                "reference_date": "2026-11-01",
                "order_count": 2,
                "revenue_bdt": 5000,
                "receipts_bdt": 3500,
                "receivable_bdt": 1500,
                "average_order_value_bdt": 2500.0,
                "expenses_bdt": 800,
                "receipts_less_expenses_bdt": 2700,
            },
            "inactive_customer_keys": ["CUST-002", "CUST-004", "CUST-005"],
            "attention_task_keys": ["TASK-001", "TASK-002", "TASK-003", "TASK-004"],
        }
        if result != expected:
            print("Restricted Day 8 results do not match reviewed fixtures.")
            return 1
        print(f"Restricted Day 8 verification passed: {json.dumps(result)}")
        return 0
    except Exception:  # noqa: BLE001 - never expose database or identity details
        print("Restricted Day 8 verification failed. Raw error suppressed.")
        return 1
    finally:
        runtime_engine.dispose()
        auth_engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())

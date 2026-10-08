"""Write and verify one idempotent synthetic task across separate processes."""

import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from database.db import connect  # noqa: E402
from database.seed import seed_database  # noqa: E402
from security.auth import demo_actor  # noqa: E402
from services.actions import execute_proposal, propose_action  # noqa: E402


TITLE = "Day 3 persistence probe"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("write", "verify"))
    parser.add_argument("--database", type=Path, required=True)
    args = parser.parse_args()
    os.environ["BIZPILOT_DEPLOYMENT_MODE"] = "demo"
    os.environ["BIZPILOT_DATA_MODE"] = "synthetic"

    if args.phase == "write":
        seed_database(args.database)
        proposal = propose_action(
            "create_task",
            {
                "title": TITLE,
                "description": "Verify durable state after process restart",
                "priority": "medium",
                "category": "operations",
            },
            demo_actor(),
            args.database,
            idempotency_key="day3-persistence-probe-v1",
        )
        execute_proposal(proposal["id"], demo_actor(), args.database)
        print("persistence_write: PASS")
        return 0

    with connect(args.database) as db:
        task_count = db.execute("SELECT COUNT(*) FROM tasks WHERE title = ?", (TITLE,)).fetchone()[0]
        execution_count = db.execute(
            "SELECT COUNT(*) FROM action_executions WHERE idempotency_key = ?",
            ("day3-persistence-probe-v1",),
        ).fetchone()[0]
        audit_count = db.execute(
            "SELECT COUNT(*) FROM audit_events WHERE event_type = 'action.executed' AND outcome = 'succeeded'"
        ).fetchone()[0]
    passed = task_count == 1 and execution_count == 1 and audit_count >= 1
    print(f"persistence_verify: {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

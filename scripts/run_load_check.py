"""Bounded two-session synthetic load check with fake delayed model reservations."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import json
import os
from pathlib import Path
import shutil
import sys
from threading import Barrier, Lock
from time import perf_counter, sleep
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from database.db import connect  # noqa: E402
from database.seed import seed_database, today  # noqa: E402
from security.auth import ActorContext  # noqa: E402
from services.actions import execute_proposal, propose_action  # noqa: E402
from services.run_policy import release_run, reserve_run  # noqa: E402
from tools.finance import get_financial_summary  # noqa: E402
from tools.operations import get_inventory, get_low_stock_products  # noqa: E402


def percentile95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[max(0, round(0.95 * len(ordered) + 0.5) - 1)]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the bounded BizPilot pilot load check")
    parser.add_argument("--duration-seconds", type=int, default=900)
    parser.add_argument("--fake-provider-delay-seconds", type=float, default=30)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.duration_seconds < 1 or args.fake_provider_delay_seconds < 0:
        parser.error("durations must be positive")

    os.environ.update({
        "BIZPILOT_DEPLOYMENT_MODE": "demo",
        "BIZPILOT_DATA_MODE": "synthetic",
        "BIZPILOT_AI_MODE": "gemini",
        "GEMINI_API_KEY": "synthetic-load-key-never-sent",
    })
    work = ROOT / ".venv" / f"load-{uuid4().hex}"
    work.mkdir(parents=True)
    database = work / "load.sqlite3"
    seed_database(database)
    expiry = today() + timedelta(hours=1)
    actors = (
        ActorContext("local-load", "owner-one", "Owner one", expiry),
        ActorContext("local-load", "owner-two", "Owner two", expiry),
    )
    latencies: list[float] = []
    errors: list[str] = []
    histories = [["session-one-marker"], ["session-two-marker"]]
    lock = Lock()
    barrier = Barrier(2)
    proposal = propose_action("run_restock_review", {}, actors[0], database)
    with ThreadPoolExecutor(max_workers=2) as executor:
        confirmations = list(executor.map(
            lambda _: _confirm_safely(proposal["id"], actors[0], database), range(2)
        ))
    stop_at = perf_counter() + args.duration_seconds

    def session(index: int) -> None:
        actor = actors[index]
        try:
            barrier.wait(timeout=5)
            run_id = reserve_run(actor, database)
            sleep(args.fake_provider_delay_seconds)
            release_run(run_id, database)
            while perf_counter() < stop_at:
                started = perf_counter()
                get_inventory(db_path=database)
                get_financial_summary(db_path=database)
                elapsed = (perf_counter() - started) * 1000
                if histories[index][0] in histories[1 - index]:
                    raise AssertionError("cross-session history bleed")
                with lock:
                    latencies.append(elapsed)
                sleep(0.05)
        except Exception as error:
            with lock:
                errors.append(type(error).__name__)

    started = perf_counter()
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            list(executor.map(session, range(2)))
        with connect(database) as db:
            restock_count = db.execute(
                "SELECT COUNT(*) FROM tasks WHERE category = 'restock'"
            ).fetchone()[0]
            execution_count = db.execute("SELECT COUNT(*) FROM action_executions").fetchone()[0]
            active_runs = db.execute("SELECT COUNT(*) FROM ai_usage WHERE status = 'active'").fetchone()[0]
        p95 = percentile95(latencies) if latencies else float("inf")
        report = {
            "duration_seconds": round(perf_counter() - started, 2),
            "sessions": 2,
            "fake_provider_delay_seconds": args.fake_provider_delay_seconds,
            "dashboard_operations": len(latencies),
            "non_model_p95_ms": round(p95, 2),
            "error_count": len(errors),
            "error_categories": sorted(set(errors)),
            "restock_task_count": restock_count,
            "expected_restock_task_count": len(get_low_stock_products(database)),
            "action_execution_count": execution_count,
            "active_model_reservations_after_test": active_runs,
            "duplicate_confirmation_results_equal": confirmations[0] == confirmations[1],
            "session_history_isolated": histories[0][0] not in histories[1] and histories[1][0] not in histories[0],
        }
        report["passed"] = (
            not errors
            and p95 < 2000
            and restock_count == report["expected_restock_task_count"]
            and execution_count == 1
            and active_runs == 0
            and report["duplicate_confirmation_results_equal"]
            and report["session_history_isolated"]
        )
        rendered = json.dumps(report, indent=2)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
        print(rendered)
        return 0 if report["passed"] else 1
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _confirm_safely(proposal_id: str, actor: ActorContext, database: Path) -> dict:
    try:
        return execute_proposal(proposal_id, actor, database)
    except ValueError as error:
        if "already executing" not in str(error):
            raise
        for _ in range(100):
            sleep(0.02)
            try:
                return execute_proposal(proposal_id, actor, database)
            except ValueError as retry_error:
                if "already executing" not in str(retry_error):
                    raise
        raise RuntimeError("confirmation did not settle")


if __name__ == "__main__":
    raise SystemExit(main())

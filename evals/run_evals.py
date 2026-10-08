"""Run synthetic BizPilot regression/holdout cases and write a reviewable report."""

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import sys
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent import ask_copilot  # noqa: E402
from database.seed import seed_database, today  # noqa: E402
from security.auth import demo_actor  # noqa: E402


def load_cases(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def score_case(case: dict, answer: str, events: list[dict]) -> tuple[bool, list[str]]:
    failures: list[str] = []
    answer_folded = answer.casefold()
    tools = [event for event in events if event.get("type") == "tool_start"]
    expected_language = case.get("expected_language")
    has_bangla = bool(any("\u0980" <= character <= "\u09ff" for character in answer))
    if expected_language == "en" and has_bangla:
        failures.append("response_language_mismatch:en")
    if expected_language == "bn" and not has_bangla:
        failures.append("response_language_mismatch:bn")
    if expected_language == "banglish" and has_bangla:
        failures.append("response_language_mismatch:banglish")
    expected_route = case.get("expected_route")
    if expected_route == "deterministic_today_finance":
        if today().date().isoformat() not in answer:
            failures.append("authoritative_today_missing")
        if tools:
            failures.append("deterministic_route_called_model_tool")
    if expected_route == "deterministic_evidence":
        if tools:
            failures.append("deterministic_evidence_called_tool")
        for term in ("source:", "queried at:"):
            if term not in answer_folded:
                failures.append(f"evidence_field_missing:{term[:-1]}")
        snapshot_phrases = ("not real-time", "real-time data na", "real-time data নয়")
        if not any(term in answer_folded for term in snapshot_phrases):
            failures.append("snapshot_limitation_missing")

    expected_tool = case.get("expected_tool")
    if expected_tool and not any(event.get("tool") == expected_tool for event in tools):
        failures.append(f"expected_tool_missing:{expected_tool}")
    expected_arguments = case.get("expected_arguments", {})
    if expected_arguments and tools:
        matching = next((event for event in tools if event.get("tool") == expected_tool), None)
        if matching:
            actual = matching.get("arguments", {})
            for key, expected in expected_arguments.items():
                if str(actual.get(key, "")).casefold() != str(expected).casefold():
                    failures.append(f"argument_mismatch:{key}")

    if case.get("expected_refusal"):
        refusal_terms = (
            "can't", "cannot", "not available", "not an available capability",
            "no data was changed", "refuse", "parbo na", "পারব না", "দেখাতে পারি না",
        )
        if not any(term in answer_folded for term in refusal_terms):
            failures.append("refusal_missing")
        if tools:
            failures.append("refusal_called_tool")

    if case.get("expected_action_status") == "pending_proposal":
        if "proposal status:" not in answer_folded or "pending" not in answer_folded:
            failures.append("pending_proposal_status_missing")
        no_execution_terms = (
            "no action was created", "কোনো action তৈরি", "kono action create",
        )
        if not any(term in answer_folded for term in no_execution_terms):
            failures.append("no_execution_status_missing")

    for text in case.get("must_include", []):
        if text.casefold() not in answer_folded:
            failures.append(f"required_text_missing:{text}")
    for alternatives in case.get("must_include_any", []):
        if not any(str(text).casefold() in answer_folded for text in alternatives):
            failures.append(f"required_alternative_missing:{'|'.join(map(str, alternatives))}")
    for text in case.get("must_not_include", []):
        if text.casefold() in answer_folded:
            failures.append(f"forbidden_text_present:{text}")
    return not failures, failures


def is_rate_limit_error(error: Exception) -> bool:
    return "rate limit or quota" in str(error).casefold()


def build_report(suite: str, live: bool, results: list[dict], planned_count: int,
                 eval_version: str = "v1") -> dict:
    return {
        "generated_at_bangladesh": today().isoformat(timespec="seconds"),
        "mode": "live" if live else "offline",
        "suite": suite,
        "eval_version": eval_version,
        "planned_case_count": planned_count,
        "case_count": len(results),
        "automated_pass_count": sum(item["passed_automated_checks"] for item in results),
        "complete": len(results) == planned_count,
        "limitations": ("Offline output is a runner smoke test and does not score model quality."
                        if not live else
                        "Automated checks do not replace human language/action review."),
        "results": results,
    }


def write_report(path: Path | None, report: dict) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def select_resume_results(results: list[dict], retry_errors: bool) -> list[dict]:
    if not retry_errors:
        return list(results)
    return [item for item in results if not item.get("error_category")]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run synthetic BizPilot language evaluations")
    parser.add_argument("--live", action="store_true",
                        help="Use configured Gemini/OpenAI API; otherwise run labeled offline mode")
    parser.add_argument("--suite", choices=("holdout", "regression", "all"), default="holdout")
    parser.add_argument("--eval-version", choices=("v1", "v2", "v3"), default="v1",
                        help="Evaluation contract and holdout version")
    parser.add_argument("--output", type=Path, help="Optional JSON report path")
    parser.add_argument("--resume", action="store_true",
                        help="Resume an incomplete report and skip recorded case IDs")
    parser.add_argument("--retry-errors", action="store_true",
                        help="With --resume, rerun only cases that recorded an error category")
    parser.add_argument("--delay-seconds", type=float, default=12.0,
                        help="Pause between live cases to reduce provider rate pressure")
    parser.add_argument("--rate-limit-wait-seconds", type=float, default=60.0,
                        help="Initial wait before retrying a rate-limited case")
    parser.add_argument("--max-rate-limit-retries", type=int, default=2,
                        help="Retry count before checkpointing and stopping")
    parser.add_argument("--max-cases", type=int,
                        help="Run only the first N selected cases for a bounded smoke check")
    args = parser.parse_args()

    if args.retry_errors and not args.resume:
        parser.error("--retry-errors requires --resume")

    os.environ["BIZPILOT_DEPLOYMENT_MODE"] = "demo"
    os.environ["BIZPILOT_DATA_MODE"] = "synthetic"
    if not args.live:
        os.environ["BIZPILOT_AI_MODE"] = "offline"
    elif os.getenv("BIZPILOT_AI_MODE", "offline").lower() == "offline":
        parser.error("--live requires BIZPILOT_AI_MODE=gemini or openai")

    cases: list[dict] = []
    if args.suite in ("holdout", "all"):
        holdout_file = {
            "v1": "holdout_cases.json",
            "v2": "holdout_v2_cases.json",
            "v3": "holdout_v3_cases.json",
        }[args.eval_version]
        cases.extend(load_cases(ROOT / "evals" / holdout_file))
    if args.suite in ("regression", "all"):
        cases.extend(load_cases(ROOT / "evals" / "banglish_cases.json"))

    if args.delay_seconds < 0 or args.rate_limit_wait_seconds < 0:
        parser.error("delay values cannot be negative")
    if args.max_rate_limit_retries < 0:
        parser.error("--max-rate-limit-retries cannot be negative")
    if args.max_cases is not None:
        if args.max_cases < 1:
            parser.error("--max-cases must be at least 1")
        cases = cases[:args.max_cases]
    case_order = {
        case.get("id", f"regression-{index + 1}"): index
        for index, case in enumerate(cases)
    }

    work = ROOT / ".venv" / f"eval-{uuid4().hex}"
    work.mkdir(parents=True)
    database = work / "eval.sqlite3"
    seed_database(database)
    results: list[dict] = []
    if args.resume:
        if args.output is None or not args.output.exists():
            parser.error("--resume requires an existing --output report")
        previous = json.loads(args.output.read_text(encoding="utf-8"))
        if (previous.get("suite") != args.suite or previous.get("mode") != "live"
                or previous.get("eval_version", "v1") != args.eval_version):
            parser.error("resume report mode/suite/version does not match this run")
        results = select_resume_results(
            list(previous.get("results", [])), args.retry_errors
        )
    completed_ids = {item.get("id") for item in results}
    stopped_for_rate_limit = False
    try:
        for index, case in enumerate(cases):
            case_id = case.get("id", f"regression-{index + 1}")
            if case_id in completed_ids:
                continue
            attempts = 0
            while True:
                history: list = []
                events: list[dict] = []
                started = datetime.now()
                try:
                    if case.get("previous_prompt"):
                        _, history = ask_copilot(case["previous_prompt"], history, database,
                                                 actor=demo_actor())
                    answer, _ = ask_copilot(case["prompt"], history, database,
                                            actor=demo_actor(), event_sink=events)
                    passed, failures = score_case(case, answer, events) if args.live else (True, [])
                    error = None
                    break
                except Exception as exc:
                    if args.live and is_rate_limit_error(exc) and attempts < args.max_rate_limit_retries:
                        wait_seconds = args.rate_limit_wait_seconds * (2 ** attempts)
                        attempts += 1
                        time.sleep(wait_seconds)
                        continue
                    answer, passed, failures = "", False, [
                        "rate_limit_or_quota" if is_rate_limit_error(exc) else "run_error"
                    ]
                    error = "rate_limit_or_quota" if is_rate_limit_error(exc) else type(exc).__name__
                    stopped_for_rate_limit = is_rate_limit_error(exc)
                    break
            results.append({
                "id": case_id,
                "language": case.get("language", "banglish_or_bn"),
                "prompt": case["prompt"],
                "answer": answer,
                "events": events,
                "passed_automated_checks": passed,
                "failures": failures,
                "error_category": error,
                "latency_ms": round((datetime.now() - started).total_seconds() * 1000, 2),
                "requires_human_language_review": args.live,
            })
            results.sort(key=lambda item: case_order.get(item.get("id"), len(cases)))
            write_report(args.output, build_report(
                args.suite, args.live, results, len(cases), args.eval_version
            ))
            if stopped_for_rate_limit:
                break
            if args.live and args.delay_seconds:
                time.sleep(args.delay_seconds)
    finally:
        shutil.rmtree(work, ignore_errors=True)

    report = build_report(args.suite, args.live, results, len(cases), args.eval_version)
    write_report(args.output, report)
    print(json.dumps({key: report[key] for key in (
        "generated_at_bangladesh", "mode", "suite", "eval_version", "case_count",
        "automated_pass_count", "limitations")}, ensure_ascii=False, indent=2))
    return 0 if report["complete"] and all(
        item["passed_automated_checks"] for item in results
    ) else 1


if __name__ == "__main__":
    sys.exit(main())

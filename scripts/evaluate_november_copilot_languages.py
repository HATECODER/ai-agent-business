"""Validate the frozen November Copilot prompt set without a model call."""

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.copilot import classify_question, detect_language

CASES_PATH = ROOT / "evals" / "november_demo_language_cases.json"
EXPECTED_LANGUAGES = {"English", "Bangla", "Banglish"}
EXPECTED_QUESTION_TYPES = {
    "restock",
    "finance",
    "inactive_customers",
    "tasks",
    "restock_proposal",
}


def evaluate_cases(path: Path = CASES_PATH) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload.get("cases", [])
    if len(cases) != 15:
        raise ValueError("Language evaluation must contain exactly 15 cases.")
    ids = [case["id"] for case in cases]
    if len(set(ids)) != len(ids):
        raise ValueError("Language evaluation case IDs must be unique.")

    language_counts = Counter(case["language"] for case in cases)
    if set(language_counts) != EXPECTED_LANGUAGES or set(language_counts.values()) != {
        5
    }:
        raise ValueError("Each supported language must contain five cases.")
    question_counts = Counter(case["expected_question_type"] for case in cases)
    if set(question_counts) != EXPECTED_QUESTION_TYPES or set(
        question_counts.values()
    ) != {3}:
        raise ValueError("Each supported question must appear once per language.")

    failures = []
    for case in cases:
        actual = classify_question(case["prompt"]).value
        actual_language = detect_language(case["prompt"])
        if (
            actual != case["expected_question_type"]
            or actual_language != case["language"]
        ):
            failures.append(
                {
                    "id": case["id"],
                    "expected": case["expected_question_type"],
                    "actual": actual,
                    "expected_language": case["language"],
                    "actual_language": actual_language,
                }
            )
    return {
        "version": payload["version"],
        "total": len(cases),
        "passed": len(cases) - len(failures),
        "failed": len(failures),
        "language_counts": dict(sorted(language_counts.items())),
        "question_counts": dict(sorted(question_counts.items())),
        "failures": failures,
    }


def main() -> int:
    result = evaluate_cases()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

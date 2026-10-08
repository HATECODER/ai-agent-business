"""Fast repository policy checks for the BUILD security gate.

This complements secret, static, dependency, test, and container checks. It
does not claim that future PILOT or PRODUCTION requirements are implemented.
"""

from __future__ import annotations

import argparse
from pathlib import Path
# This module runs a fixed Git argv and never enables shell execution.
import subprocess  # nosec B404
import sys


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = (
    "SECURITY_REQUIREMENTS.md",
    ".github/workflows/test.yml",
    ".github/pull_request_template.md",
    ".gitignore",
    ".env.example",
    "requirements.lock.txt",
    "requirements-dev.txt",
    "scripts/check_secrets.py",
    "scripts/security_gate.ps1",
)

REQUIRED_IGNORES = (
    ".env",
    ".venv/",
    "*.sqlite3",
    ".streamlit/secrets.toml",
    "backups/",
)

REQUIRED_WORKFLOW_MARKERS = (
    "push:",
    "pull_request:",
    "permissions:\n  contents: read",
    "python scripts/check_security_requirements.py --stage build",
    "python scripts/check_secrets.py",
    "ruff check",
    "bandit",
    "pip-audit",
    "pytest",
    "run_load_check.py",
    "docker build",
)

SENSITIVE_ENV_MARKERS = (
    "API_KEY",
    "SECRET",
    "PASSWORD",
    "ACCESS_TOKEN",
    "DATABASE_URL",
    "OWNER_SUBJECTS",
)

FORBIDDEN_TRACKED_NAMES = {
    ".env",
    ".streamlit/secrets.toml",
}

FORBIDDEN_TRACKED_SUFFIXES = (
    ".sqlite3",
    ".sqlite3-shm",
    ".sqlite3-wal",
    ".pem",
    ".p12",
    ".pfx",
)


def _tracked_files() -> list[str]:
    output = subprocess.check_output(  # nosec B603 B607
        ["git", "ls-files", "-z"], cwd=ROOT, stderr=subprocess.DEVNULL
    )
    return [item.decode("utf-8", errors="replace") for item in output.split(b"\0") if item]


def _record(results: list[tuple[str, bool, str]], check_id: str,
            passed: bool, detail: str) -> None:
    results.append((check_id, passed, detail))


def check_build_policy() -> list[tuple[str, bool, str]]:
    results: list[tuple[str, bool, str]] = []

    missing = [name for name in REQUIRED_FILES if not (ROOT / name).is_file()]
    _record(results, "SEC-BLD-001A", not missing,
            "required security files present" if not missing else f"missing: {', '.join(missing)}")

    ignore_text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    ignore_lines = ignore_text.splitlines()
    missing_ignores = [value for value in REQUIRED_IGNORES if value not in ignore_lines]
    _record(results, "SEC-BLD-001B", not missing_ignores,
            "sensitive local artifacts are ignored" if not missing_ignores
            else f"missing ignore rules: {', '.join(missing_ignores)}")

    forbidden = []
    for name in _tracked_files():
        normalized = name.replace("\\", "/")
        if normalized in FORBIDDEN_TRACKED_NAMES or normalized.startswith("backups/"):
            forbidden.append(name)
        elif normalized.lower().endswith(FORBIDDEN_TRACKED_SUFFIXES):
            forbidden.append(name)
    _record(results, "SEC-BLD-001C", not forbidden,
            "no forbidden secret/data artifacts are tracked" if not forbidden
            else f"forbidden tracked paths: {', '.join(forbidden)}")

    unsafe_examples = []
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    for raw_line in env_example.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if any(marker in key.upper() for marker in SENSITIVE_ENV_MARKERS) and value.strip():
            unsafe_examples.append(key)
    _record(results, "SEC-SEC-001", not unsafe_examples,
            "sensitive .env.example values are empty" if not unsafe_examples
            else f"nonempty sensitive example values: {', '.join(unsafe_examples)}")

    workflow = (ROOT / ".github/workflows/test.yml").read_text(encoding="utf-8")
    missing_markers = [marker for marker in REQUIRED_WORKFLOW_MARKERS if marker not in workflow]
    _record(results, "SEC-SUP-003", not missing_markers,
            "push/PR workflow contains required BUILD checks" if not missing_markers
            else f"workflow markers missing: {', '.join(missing_markers)}")

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Check BizPilot security requirements for a release stage.")
    parser.add_argument("--stage", choices=("build",), default="build",
                        help="Only BUILD is automated until later-stage features exist.")
    args = parser.parse_args()

    results = check_build_policy() if args.stage == "build" else []
    failed = False
    for check_id, passed, detail in results:
        label = "PASS" if passed else "FAIL"
        print(f"[{label}] {check_id}: {detail}")
        failed = failed or not passed

    if failed:
        print("BUILD security policy gate failed.")
        return 1
    print("BUILD security policy gate passed. Later-stage requirements remain feature/release gates.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

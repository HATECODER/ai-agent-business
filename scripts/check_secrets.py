"""Fail when tracked files or Git patches contain common live API-key shapes.

Only file names are reported. Secret-looking values are never printed.
"""

from pathlib import Path
import re
# This module runs fixed git argv only; shell execution is never used.
import subprocess  # nosec B404
import sys


ROOT = Path(__file__).resolve().parents[1]
PATTERNS = (
    re.compile(("AI" + "zaSy" + r"[A-Za-z0-9_-]{20,}").encode()),
    re.compile(("s" + "k-" + r"[A-Za-z0-9_-]{20,}").encode()),
    re.compile(("A" + "Q" + r"\." + r"[A-Za-z0-9_-]{20,}").encode()),
)


def contains_secret(data: bytes) -> bool:
    return any(pattern.search(data) for pattern in PATTERNS)


def git(*args: str) -> bytes:
    # Arguments come only from fixed call sites in this file, never from users.
    return subprocess.check_output(  # nosec B603 B607
        ["git", *args], cwd=ROOT, stderr=subprocess.DEVNULL
    )


def main() -> int:
    findings: list[str] = []
    # Include new non-ignored files so a local pre-commit scan covers the whole
    # proposed change, not only files that are already tracked.
    for raw_name in git("ls-files", "--cached", "--others", "--exclude-standard", "-z").split(b"\0"):
        if not raw_name:
            continue
        name = raw_name.decode("utf-8", errors="replace")
        if name == "scripts/check_secrets.py":
            continue
        path = ROOT / name
        if path.is_file() and contains_secret(path.read_bytes()):
            findings.append(name)

    history = git("log", "-p", "--all", "--no-ext-diff", "--", ".")
    if contains_secret(history):
        findings.append("<git history patch>")

    if findings:
        print("Secret scan failed in: " + ", ".join(sorted(set(findings))))
        print("Values are redacted. Remove/rotate the credential before release.")
        return 1
    print("Secret scan passed for tracked/new files and Git history patches.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

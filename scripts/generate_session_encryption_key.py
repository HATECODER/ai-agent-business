"""Generate the local Redis session encryption key without displaying it."""

from __future__ import annotations

from pathlib import Path
import secrets


ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
KEY = "BIZPILOT_SESSION_ENCRYPTION_KEY"


def main() -> int:
    value = secrets.token_hex(32)
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    updated: list[str] = []
    replaced = False
    for line in lines:
        if line.split("=", 1)[0] == KEY:
            if not replaced:
                updated.append(f"{KEY}={value}")
                replaced = True
            continue
        updated.append(line)
    if not replaced:
        updated.append(f"{KEY}={value}")
    ENV_PATH.write_text("\n".join(updated) + "\n", encoding="utf-8")
    print("BIZPILOT_SESSION_ENCRYPTION_KEY generated without displaying it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

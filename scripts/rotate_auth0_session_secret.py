"""Rotate the local Auth0 application-cookie secret without printing it."""

from __future__ import annotations

from pathlib import Path
import secrets


ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
KEY = "AUTH0_SECRET"


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
    print("AUTH0_SECRET rotated locally without displaying the credential.")
    print("Copy it from .env to the Render staging web service and redeploy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Fail-closed deployment checks that never print credentials or identities."""

from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import (  # noqa: E402
    ai_mode,
    data_mode,
    deployment_mode,
    gemini_key_available,
    owner_subject_allowlist,
)
from database.db import database_path, prepare_database  # noqa: E402


def main() -> int:
    checks = {
        "deployment_mode": deployment_mode() == "pilot",
        "synthetic_data_only": data_mode() == "synthetic",
        "gemini_provider": ai_mode() == "gemini",
        "provider_key_present": gemini_key_available(),
        "one_or_two_owners": 1 <= len(owner_subject_allowlist()) <= 2,
        "oidc_config_present": (ROOT / ".streamlit" / "secrets.toml").is_file(),
    }
    try:
        prepare_database()
        path = database_path()
        connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
        try:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        finally:
            connection.close()
        checks["database_present"] = True
        checks["database_integrity"] = integrity == "ok"
    except Exception:
        checks["database_present"] = False
        checks["database_integrity"] = False

    for name, passed in checks.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())

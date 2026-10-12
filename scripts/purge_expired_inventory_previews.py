"""Delete expired CSV preview metadata using a temporary migration credential."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.database import create_database_engine
from backend.app.inventory_import import (
    ImportPreviewUnavailable,
    purge_expired_import_metadata,
)

ENV_PATH = ROOT / ".env"
MIGRATION_KEY = "BIZPILOT_MIGRATION_DATABASE_URL"


def _remove_migration_credential() -> None:
    if not ENV_PATH.exists():
        return
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    kept = [line for line in lines if line.split("=", 1)[0] != MIGRATION_KEY]
    ENV_PATH.write_text("\n".join(kept) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Confirm deletion of all expired preview metadata.",
    )
    arguments = parser.parse_args()
    if not arguments.execute:
        print("Dry run only. Pass --execute to delete expired preview metadata.")
        return 0

    migration_url = (dotenv_values(ENV_PATH).get(MIGRATION_KEY) or "").strip()
    if not migration_url:
        print("Temporary migration URL is required. No changes made.")
        return 1
    if not migration_url.startswith(("postgresql://", "postgresql+psycopg://")):
        print("Migration URL must use PostgreSQL. No changes made.")
        _remove_migration_credential()
        return 1

    engine = None
    try:
        engine = create_database_engine(migration_url)
        deleted = purge_expired_import_metadata(engine)
        print(f"Expired preview records deleted: {deleted}")
        return 0
    except (ImportPreviewUnavailable, RuntimeError, ValueError):
        print("Preview metadata cleanup failed. No credential details were displayed.")
        return 1
    finally:
        if engine is not None:
            engine.dispose()
        _remove_migration_credential()


if __name__ == "__main__":
    raise SystemExit(main())

"""Command-line SQLite backup/restore using the supported online backup API."""

import argparse
import json
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.recovery import backup_database, logical_snapshot, restore_database  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Back up or restore BizPilot SQLite safely")
    subparsers = parser.add_subparsers(dest="command", required=True)
    backup = subparsers.add_parser("backup")
    backup.add_argument("--source", type=Path, required=True)
    backup.add_argument("--output", type=Path, required=True)
    backup.add_argument("--replace", action="store_true")
    restore = subparsers.add_parser("restore")
    restore.add_argument("--backup", type=Path, required=True)
    restore.add_argument("--target", type=Path, required=True)
    restore.add_argument("--replace", action="store_true")
    verify = subparsers.add_parser("verify")
    verify.add_argument("--database", type=Path, required=True)
    args = parser.parse_args()

    started = perf_counter()
    if args.command == "backup":
        snapshot = backup_database(args.source, args.output, replace=args.replace)
    elif args.command == "restore":
        snapshot = restore_database(args.backup, args.target, replace=args.replace)
    else:
        snapshot = logical_snapshot(args.database)
    summary = {
        "command": args.command,
        "duration_ms": round((perf_counter() - started) * 1000, 2),
        "schema_version": snapshot["schema_version"],
        "table_counts": {
            table: details["count"] for table, details in snapshot["tables"].items()
        },
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

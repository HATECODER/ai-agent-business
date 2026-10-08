"""Consistent SQLite backup, restore, and logical verification helpers."""

import hashlib
import json
import os
from pathlib import Path
import sqlite3
from uuid import uuid4

from database.db import database_path


TABLE_SELECTS = {
    "customers": "SELECT * FROM customers ORDER BY rowid",
    "products": "SELECT * FROM products ORDER BY rowid",
    "inventory": "SELECT * FROM inventory ORDER BY rowid",
    "orders": "SELECT * FROM orders ORDER BY rowid",
    "expenses": "SELECT * FROM expenses ORDER BY rowid",
    "tasks": "SELECT * FROM tasks ORDER BY rowid",
    "campaigns": "SELECT * FROM campaigns ORDER BY rowid",
    "action_proposals": "SELECT * FROM action_proposals ORDER BY rowid",
    "action_executions": "SELECT * FROM action_executions ORDER BY rowid",
    "audit_events": "SELECT * FROM audit_events ORDER BY rowid",
    "ai_usage": "SELECT * FROM ai_usage ORDER BY rowid",
}


def logical_snapshot(path: str | Path) -> dict:
    source = database_path(path)
    connection = _readonly(source)
    try:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError("SQLite integrity check failed.")
        snapshot: dict[str, object] = {
            "schema_version": connection.execute("PRAGMA user_version").fetchone()[0],
            "tables": {},
        }
        for table, select_query in TABLE_SELECTS.items():
            exists = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
            ).fetchone()
            if not exists:
                raise RuntimeError(f"Required table is missing: {table}")
            rows = [dict(row) for row in connection.execute(select_query)]
            encoded = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            snapshot["tables"][table] = {
                "count": len(rows),
                "sha256": hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
            }
        return snapshot
    finally:
        connection.close()


def backup_database(source: str | Path, destination: str | Path, *, replace: bool = False) -> dict:
    source_path = database_path(source)
    destination_path = Path(destination).expanduser().resolve()
    _different_paths(source_path, destination_path)
    if destination_path.exists() and not replace:
        raise FileExistsError("Backup destination already exists; use explicit replacement.")
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination_path.with_name(f".{destination_path.name}.{uuid4().hex}.tmp")
    source_db = _readonly(source_path)
    target_db = sqlite3.connect(temporary)
    try:
        source_db.backup(target_db)
        target_db.commit()
    finally:
        target_db.close()
        source_db.close()
    try:
        snapshot = logical_snapshot(temporary)
        os.replace(temporary, destination_path)
    finally:
        if temporary.exists():
            temporary.unlink()
    return snapshot


def restore_database(backup: str | Path, target: str | Path, *, replace: bool = False) -> dict:
    backup_path = database_path(backup)
    target_path = Path(target).expanduser().resolve()
    _different_paths(backup_path, target_path)
    if target_path.exists() and not replace:
        raise FileExistsError("Restore target already exists; use explicit replacement.")
    expected = logical_snapshot(backup_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = target_path.with_name(f".{target_path.name}.{uuid4().hex}.tmp")
    source_db = _readonly(backup_path)
    target_db = sqlite3.connect(temporary)
    try:
        source_db.backup(target_db)
        target_db.commit()
    finally:
        target_db.close()
        source_db.close()
    try:
        actual = logical_snapshot(temporary)
        if actual != expected:
            raise RuntimeError("Restored database does not match the backup logical snapshot.")
        os.replace(temporary, target_path)
    finally:
        if temporary.exists():
            temporary.unlink()
    return actual


def _readonly(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise FileNotFoundError(f"SQLite database does not exist: {path}")
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def _different_paths(first: Path, second: Path) -> None:
    if first == second:
        raise ValueError("Source and destination paths must differ.")

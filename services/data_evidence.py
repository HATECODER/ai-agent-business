"""Data provenance and bounded presentation helpers."""

from pathlib import Path

from config import data_mode, data_source_label, dataset_version, max_result_rows
from database.db import connect
from database.seed import today


def data_evidence(db_path: str | Path | None = None) -> dict:
    with connect(db_path) as db:
        row = db.execute("SELECT MIN(created_at) AS seeded_at FROM customers").fetchone()
    return {
        "source": data_source_label(),
        "data_mode": data_mode(),
        "dataset_version": dataset_version(),
        "dataset_seeded_at": row["seeded_at"] if row else None,
        "queried_at": today().isoformat(timespec="seconds"),
        "freshness": "fictional_snapshot" if data_mode() == "synthetic" else "unknown",
    }


def bounded_rows(rows: list[dict], limit: int | None = None) -> dict:
    row_limit = limit or max_result_rows()
    total = len(rows)
    return {
        "items": rows[:row_limit],
        "total_count": total,
        "returned_count": min(total, row_limit),
        "truncated": total > row_limit,
    }

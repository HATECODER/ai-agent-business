"""Idempotent restock review task creation."""

from pathlib import Path
from database.db import connect
from database.seed import today


def run_low_stock_workflow(db_path: str | Path | None = None) -> dict:
    with connect(db_path) as db:
        # One transaction and a partial unique index guard repeated executions.
        items = db.execute("""SELECT i.id, p.name, i.variant_name, i.quantity,
            i.low_stock_threshold FROM inventory i
            JOIN products p ON p.id = i.product_id WHERE p.active = 1""").fetchall()
        created = existing = 0
        for item in items:
            if item["quantity"] > item["low_stock_threshold"]:
                continue
            open_task = db.execute("""SELECT 1 FROM tasks WHERE category = 'restock'
                AND related_entity_type = 'inventory' AND related_entity_id = ?
                AND status IN ('pending', 'in_progress')""", (item["id"],)).fetchone()
            if open_task:
                existing += 1
                continue
            db.execute("""INSERT INTO tasks
                (title, description, category, priority, status, related_entity_type,
                 related_entity_id, created_at) VALUES (?, ?, 'restock', 'high',
                 'pending', 'inventory', ?, ?)""",
                (f"Review restock: {item['name']} {item['variant_name']}",
                 f"{item['quantity']} units remain; threshold is {item['low_stock_threshold']}.",
                 item["id"], today().isoformat(timespec="seconds")))
            created += 1
    return {"checked": len(items), "low_stock_items": created + existing,
            "tasks_created": created, "tasks_already_existing": existing}

"""Inventory and task operations. No model supplies business values."""

from pathlib import Path
import sqlite3

from database.db import connect
from database.models import TaskInput
from database.seed import today


INVENTORY_QUERY = """SELECT i.id AS inventory_id, p.id AS product_id, p.name AS product,
    i.variant_name, i.color, i.size, i.quantity, i.low_stock_threshold,
    p.base_price FROM inventory i JOIN products p ON p.id = i.product_id
    WHERE p.active = 1"""


def get_inventory(product_name: str = "", size: str = "", color: str = "",
                  db_path: str | Path | None = None) -> list[dict]:
    clauses = []
    params: list[str] = []
    if product_name.strip():
        clauses.append("LOWER(p.name) LIKE ?")
        params.append(f"%{product_name.strip().lower()}%")
    if size.strip():
        clauses.append("LOWER(i.size) = ?")
        params.append(size.strip().lower())
    if color.strip():
        clauses.append("LOWER(i.color) = ?")
        params.append(color.strip().lower())
    query = INVENTORY_QUERY + (" AND " + " AND ".join(clauses) if clauses else "")
    with connect(db_path) as db:
        return [dict(row) for row in db.execute(query + " ORDER BY p.name, i.variant_name", params)]


def get_low_stock_products(db_path: str | Path | None = None) -> list[dict]:
    with connect(db_path) as db:
        return [dict(row) for row in db.execute(
            INVENTORY_QUERY + " AND i.quantity <= i.low_stock_threshold ORDER BY i.quantity, p.name")]


def create_task(title: str, description: str, priority: str = "medium",
                category: str = "operations", related_entity_type: str | None = None,
                related_entity_id: int | None = None,
                db_path: str | Path | None = None) -> dict:
    task = TaskInput(title=title, description=description, priority=priority,
                     category=category, related_entity_type=related_entity_type,
                     related_entity_id=related_entity_id)
    if (task.related_entity_type is None) != (task.related_entity_id is None):
        raise ValueError("Related entity type and id must be provided together.")
    if task.category == "restock" and task.related_entity_type != "inventory":
        raise ValueError("Restock tasks must reference an inventory item.")
    with connect(db_path) as db:
        if task.category == "restock":
            existing = db.execute("""SELECT * FROM tasks WHERE category = 'restock'
                AND related_entity_type = 'inventory' AND related_entity_id = ?
                AND status IN ('pending', 'in_progress')""",
                (task.related_entity_id,)).fetchone()
            if existing:
                return {**dict(existing), "created": False}
        try:
            cursor = db.execute("""INSERT INTO tasks
                (title, description, category, priority, status, related_entity_type,
                 related_entity_id, created_at) VALUES (?, ?, ?, ?, 'pending', ?, ?, ?)""",
                (task.title, task.description, task.category, task.priority,
                 task.related_entity_type, task.related_entity_id, today().isoformat(timespec="seconds")))
        except sqlite3.IntegrityError as error:
            raise ValueError("An equivalent open restock task already exists or the related item is invalid.") from error
        result = dict(db.execute("SELECT * FROM tasks WHERE id = ?", (cursor.lastrowid,)).fetchone())
        return {**result, "created": True}


def get_pending_tasks(category: str = "", priority: str = "",
                      db_path: str | Path | None = None) -> list[dict]:
    query = "SELECT * FROM tasks WHERE status IN ('pending', 'in_progress')"
    params = []
    if category.strip():
        query += " AND category = ?"
        params.append(category.strip())
    if priority.strip():
        if priority not in ("low", "medium", "high", "critical"):
            raise ValueError("Invalid priority.")
        query += " AND priority = ?"
        params.append(priority)
    with connect(db_path) as db:
        return [dict(row) for row in db.execute(query + " ORDER BY CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, id", params)]

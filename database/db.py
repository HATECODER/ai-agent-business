"""Small SQLite connection and initialization helpers."""

from contextlib import contextmanager
from pathlib import Path
import os
import sqlite3


DEFAULT_DB = Path(__file__).resolve().parents[1] / "bizpilot.sqlite3"


def database_path(path: str | Path | None = None) -> Path:
    return Path(path or os.getenv("BIZPILOT_DB_PATH") or DEFAULT_DB).expanduser().resolve()


@contextmanager
def connect(path: str | Path | None = None):
    db_file = database_path(path)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_file, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database(path: str | Path | None = None) -> None:
    with connect(path) as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY, name TEXT NOT NULL, phone TEXT NOT NULL UNIQUE,
            preferred_language TEXT NOT NULL, preferred_category TEXT,
            preferred_size TEXT, preferred_payment_method TEXT,
            last_purchase_at TEXT, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL,
            description TEXT NOT NULL, base_price INTEGER NOT NULL CHECK(base_price >= 0),
            active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY, product_id INTEGER NOT NULL REFERENCES products(id),
            variant_name TEXT NOT NULL, color TEXT NOT NULL, size TEXT NOT NULL,
            quantity INTEGER NOT NULL CHECK(quantity >= 0),
            low_stock_threshold INTEGER NOT NULL CHECK(low_stock_threshold >= 0),
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customers(id),
            order_date TEXT NOT NULL, status TEXT NOT NULL,
            total_amount INTEGER NOT NULL CHECK(total_amount >= 0),
            payment_status TEXT NOT NULL, amount_received INTEGER NOT NULL
                CHECK(amount_received >= 0 AND amount_received <= total_amount),
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY, expense_date TEXT NOT NULL, category TEXT NOT NULL,
            description TEXT NOT NULL, amount INTEGER NOT NULL CHECK(amount >= 0),
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL,
            category TEXT NOT NULL, priority TEXT NOT NULL, status TEXT NOT NULL,
            related_entity_type TEXT, related_entity_id INTEGER,
            created_at TEXT NOT NULL, due_at TEXT, completed_at TEXT
        );
        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY, name TEXT NOT NULL, campaign_type TEXT NOT NULL,
            target_description TEXT NOT NULL, offer TEXT, channel TEXT NOT NULL,
            status TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS one_open_restock_task
          ON tasks(category, related_entity_type, related_entity_id)
          WHERE category = 'restock' AND status IN ('pending', 'in_progress');
        """)


def ensure_demo_data(path: str | Path | None = None) -> None:
    initialize_database(path)
    with connect(path) as db:
        exists = db.execute("SELECT 1 FROM customers LIMIT 1").fetchone()
    if not exists:
        from database.seed import seed_database
        seed_database(path)

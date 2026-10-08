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
            target_description TEXT NOT NULL, objective TEXT, offer TEXT, channel TEXT NOT NULL,
            status TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS action_proposals (
            id TEXT PRIMARY KEY, actor_id TEXT NOT NULL, action_type TEXT NOT NULL,
            payload_json TEXT NOT NULL, payload_hash TEXT NOT NULL,
            idempotency_key TEXT NOT NULL UNIQUE, status TEXT NOT NULL,
            created_at TEXT NOT NULL, expires_at TEXT NOT NULL,
            decided_at TEXT, result_json TEXT
        );
        CREATE TABLE IF NOT EXISTS action_executions (
            idempotency_key TEXT PRIMARY KEY, proposal_id TEXT NOT NULL UNIQUE,
            payload_hash TEXT NOT NULL, status TEXT NOT NULL,
            started_at TEXT NOT NULL, completed_at TEXT, result_json TEXT,
            FOREIGN KEY(proposal_id) REFERENCES action_proposals(id)
        );
        CREATE TABLE IF NOT EXISTS audit_events (
            id INTEGER PRIMARY KEY, actor_id TEXT NOT NULL, event_type TEXT NOT NULL,
            target_type TEXT NOT NULL, target_id TEXT NOT NULL,
            outcome TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS ai_usage (
            run_id TEXT PRIMARY KEY, actor_id TEXT NOT NULL, provider TEXT NOT NULL,
            model TEXT NOT NULL, usage_date TEXT NOT NULL,
            reserved_usd_micros INTEGER NOT NULL CHECK(reserved_usd_micros >= 0),
            actual_usd_micros INTEGER,
            status TEXT NOT NULL, input_tokens INTEGER, output_tokens INTEGER,
            model_calls INTEGER, tool_calls INTEGER,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS ai_usage_daily_actor
          ON ai_usage(usage_date, actor_id, status);
        CREATE UNIQUE INDEX IF NOT EXISTS one_open_restock_task
          ON tasks(category, related_entity_type, related_entity_id)
          WHERE category = 'restock' AND status IN ('pending', 'in_progress');
        """)
        campaign_columns = {row[1] for row in db.execute("PRAGMA table_info(campaigns)")}
        if "objective" not in campaign_columns:
            db.execute("ALTER TABLE campaigns ADD COLUMN objective TEXT")


def ensure_demo_data(path: str | Path | None = None) -> None:
    initialize_database(path)
    with connect(path) as db:
        exists = db.execute("SELECT 1 FROM customers LIMIT 1").fetchone()
    if not exists:
        from database.seed import seed_database
        seed_database(path)


def prepare_database(path: str | Path | None = None) -> None:
    """Prepare demo storage or validate a pre-provisioned pilot database.

    Pilot startup deliberately does not create a database or seed records.
    """
    from config import data_mode, deployment_mode

    data_mode()  # Validate the configured combination before touching disk.
    if deployment_mode() == "demo":
        ensure_demo_data(path)
        return

    db_file = database_path(path)
    if not db_file.is_file():
        raise RuntimeError(
            "Pilot database is missing. Provision and seed the synthetic dataset explicitly before startup."
        )
    connection = sqlite3.connect(f"file:{db_file.as_posix()}?mode=ro", uri=True)
    try:
        tables = {row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )}
    finally:
        connection.close()
    required = {
        "customers", "products", "inventory", "orders", "expenses", "tasks", "campaigns",
        "action_proposals", "action_executions", "audit_events", "ai_usage",
    }
    missing = sorted(required - tables)
    if missing:
        raise RuntimeError(f"Pilot database schema is incomplete: {', '.join(missing)}")

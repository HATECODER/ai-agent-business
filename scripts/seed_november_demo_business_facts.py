"""Migrate and seed November finance, customer, order, expense, and task facts."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from uuid import UUID, uuid5

import psycopg
from alembic import command
from alembic.config import Config
from dotenv import dotenv_values
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
FIXTURE_DIR = ROOT / "demo_fixtures" / "november_v1"
MIGRATION_KEY = "BIZPILOT_MIGRATION_DATABASE_URL"
WORKSPACE_KEY = "BIZPILOT_WORKSPACE_ID"
SOURCE_REFERENCE = "bizpilot-november-demo"


def _rows(name: str) -> list[dict[str, str]]:
    with (FIXTURE_DIR / name).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _stable_id(workspace_id: UUID, kind: str, key: str) -> UUID:
    return uuid5(workspace_id, f"{SOURCE_REFERENCE}:{kind}:{key}")


def _configuration() -> tuple[str, UUID]:
    values = dotenv_values(ENV_PATH)
    admin_url = (values.get(MIGRATION_KEY) or "").strip()
    parsed = urlsplit(admin_url.replace("postgresql+psycopg://", "postgresql://", 1))
    if (
        not admin_url.startswith("postgresql+psycopg://")
        or not parsed.hostname
        or not parsed.hostname.endswith(".pooler.supabase.com")
        or parsed.port != 5432
        or not (parsed.username or "").startswith("postgres.")
        or parse_qs(parsed.query).get("sslmode") != ["require"]
    ):
        raise RuntimeError("Migration URL must be the TLS Supabase session pooler URL.")
    try:
        workspace_id = UUID((values.get(WORKSPACE_KEY) or "").strip())
    except (TypeError, ValueError, AttributeError) as error:
        raise RuntimeError("Staging workspace ID is invalid.") from error
    return admin_url, workspace_id


def _remove_migration_credential() -> None:
    if not ENV_PATH.exists():
        return
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    kept = [line for line in lines if line.split("=", 1)[0] != MIGRATION_KEY]
    ENV_PATH.write_text("\n".join(kept) + "\n", encoding="utf-8")


def _migrate(admin_url: str) -> None:
    config = Config(str(ROOT / "backend" / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", admin_url.replace("%", "%%"))
    command.upgrade(config, "head")


def seed(connection: psycopg.Connection, workspace_id: UUID) -> dict[str, int]:
    manifest = json.loads((FIXTURE_DIR / "manifest.json").read_text(encoding="utf-8"))
    version = manifest["fixture_version"]
    observed_at = datetime.fromisoformat(f"{manifest['reference_date']}T00:00:00+06:00")
    exists = connection.execute(
        "SELECT 1 FROM tenants WHERE id = %s AND status = 'active'", (workspace_id,)
    ).fetchone()
    if exists is None:
        raise RuntimeError("Configured active staging workspace was not found.")

    customer_ids: dict[str, UUID] = {}
    for row in _rows("customers.csv"):
        customer_id = _stable_id(workspace_id, "customer", row["customer_key"])
        customer_ids[row["customer_key"]] = customer_id
        connection.execute(
            """
            INSERT INTO customers
                (id, tenant_id, customer_key, display_name, source_reference,
                 source_version, observed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (tenant_id, customer_key) DO UPDATE SET
                display_name = EXCLUDED.display_name,
                source_reference = EXCLUDED.source_reference,
                source_version = EXCLUDED.source_version,
                observed_at = EXCLUDED.observed_at
            """,
            (customer_id, workspace_id, row["customer_key"], row["display_name"], SOURCE_REFERENCE, version, observed_at),
        )

    for row in _rows("orders.csv"):
        connection.execute(
            """
            INSERT INTO orders
                (id, tenant_id, customer_id, order_key, order_date, status,
                 total_amount_minor, amount_received_minor, currency,
                 source_reference, source_version, observed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'BDT', %s, %s, %s)
            ON CONFLICT (tenant_id, order_key) DO UPDATE SET
                customer_id = EXCLUDED.customer_id, order_date = EXCLUDED.order_date,
                status = EXCLUDED.status, total_amount_minor = EXCLUDED.total_amount_minor,
                amount_received_minor = EXCLUDED.amount_received_minor,
                source_reference = EXCLUDED.source_reference,
                source_version = EXCLUDED.source_version, observed_at = EXCLUDED.observed_at
            """,
            (
                _stable_id(workspace_id, "order", row["order_key"]), workspace_id,
                customer_ids[row["customer_key"]], row["order_key"], row["order_date"],
                row["status"], int(row["total_amount_bdt"]) * 100,
                int(row["amount_received_bdt"]) * 100, SOURCE_REFERENCE, version, observed_at,
            ),
        )

    for row in _rows("expenses.csv"):
        connection.execute(
            """
            INSERT INTO expenses
                (id, tenant_id, expense_key, expense_date, category, description,
                 amount_minor, currency, source_reference, source_version, observed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'BDT', %s, %s, %s)
            ON CONFLICT (tenant_id, expense_key) DO UPDATE SET
                expense_date = EXCLUDED.expense_date, category = EXCLUDED.category,
                description = EXCLUDED.description, amount_minor = EXCLUDED.amount_minor,
                source_reference = EXCLUDED.source_reference,
                source_version = EXCLUDED.source_version, observed_at = EXCLUDED.observed_at
            """,
            (
                _stable_id(workspace_id, "expense", row["expense_key"]), workspace_id,
                row["expense_key"], row["expense_date"], row["category"], row["description"],
                int(row["amount_bdt"]) * 100, SOURCE_REFERENCE, version, observed_at,
            ),
        )

    for row in _rows("tasks.csv"):
        connection.execute(
            """
            INSERT INTO tasks
                (id, tenant_id, task_key, title, category, priority, status,
                 source_reference, source_version, observed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (tenant_id, task_key) DO UPDATE SET
                title = EXCLUDED.title, category = EXCLUDED.category,
                priority = EXCLUDED.priority, status = EXCLUDED.status,
                source_reference = EXCLUDED.source_reference,
                source_version = EXCLUDED.source_version, observed_at = EXCLUDED.observed_at
            """,
            (
                _stable_id(workspace_id, "task", row["task_key"]), workspace_id,
                row["task_key"], row["title"], row["category"], row["priority"],
                row["status"], SOURCE_REFERENCE, version, observed_at,
            ),
        )
    return verify(connection, workspace_id, version)


def verify(connection: psycopg.Connection, workspace_id: UUID, version: str) -> dict[str, int]:
    parameters = (workspace_id, SOURCE_REFERENCE, version)
    result = {}
    for table in ("customers", "orders", "expenses", "tasks"):
        result[table] = connection.execute(
            sql.SQL(
                "SELECT COUNT(*) FROM {} WHERE tenant_id = %s "
                "AND source_reference = %s AND source_version = %s"
            ).format(sql.Identifier(table)),
            parameters,
        ).fetchone()[0]
    return result


def _assert_counts(result: dict[str, int]) -> None:
    expected = {"customers": 6, "orders": 8, "expenses": 3, "tasks": 5}
    if result != expected:
        raise RuntimeError("Database business fact counts do not match reviewed fixtures.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--action", choices=("execute", "verify"), default="verify")
    args = parser.parse_args(argv)
    remove_credential = False
    stage = "configuration"
    try:
        admin_url, workspace_id = _configuration()
        remove_credential = True
        stage = "database connection"
        connection_url = admin_url.replace("postgresql+psycopg://", "postgresql://", 1)
        with psycopg.connect(connection_url, connect_timeout=10) as connection:
            connection.execute("SELECT 1")
            connection.rollback()
        if args.action == "execute":
            stage = "schema migration"
            _migrate(admin_url)
        manifest = json.loads((FIXTURE_DIR / "manifest.json").read_text(encoding="utf-8"))
        stage = "fixture verification" if args.action == "verify" else "fixture seed"
        with psycopg.connect(connection_url, connect_timeout=10) as connection:
            if args.action == "execute":
                planned = seed(connection, workspace_id)
                _assert_counts(planned)
                connection.rollback()
                applied = seed(connection, workspace_id)
                _assert_counts(applied)
                connection.commit()
                result = {"planned": planned, "applied": applied}
            else:
                result = verify(connection, workspace_id, manifest["fixture_version"])
                _assert_counts(result)
                connection.rollback()
    except Exception as error:  # noqa: BLE001 - raw database errors stay private
        print(f"November demo business facts {args.action} failed during {stage}.")
        sqlstate = getattr(error, "sqlstate", None)
        if sqlstate:
            print(f"PostgreSQL SQLSTATE: {sqlstate}")
        print(str(error) if isinstance(error, RuntimeError) else "Raw error suppressed.")
        return 1
    finally:
        if remove_credential:
            _remove_migration_credential()
    print(f"November demo business facts {args.action} completed: {json.dumps(result)}")
    print(f"Database changes committed: {args.action == 'execute'}")
    print("Migration credential removed from .env: True")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

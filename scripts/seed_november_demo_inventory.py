"""Plan, apply, verify, or safely reset the November staging inventory seed."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from uuid import UUID, uuid5

import psycopg
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
FIXTURE_DIR = ROOT / "demo_fixtures" / "november_v1"
MIGRATION_KEY = "BIZPILOT_MIGRATION_DATABASE_URL"
WORKSPACE_ID_KEY = "BIZPILOT_WORKSPACE_ID"
SOURCE_REFERENCE = "bizpilot-november-demo"


@dataclass(frozen=True)
class SeedRow:
    product_id: UUID
    variant_id: UUID
    balance_id: UUID
    location_id: UUID
    product_name: str
    variant_name: str
    sku: str
    location_code: str
    location_name: str
    quantity: int
    low_stock_threshold: int
    options: dict[str, str]
    base_price_minor: int | None
    record_version: int


def _csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _stable_id(workspace_id: UUID, kind: str, key: str) -> UUID:
    return uuid5(workspace_id, f"{SOURCE_REFERENCE}:{kind}:{key}")


def load_seed_rows(
    workspace_id: UUID, fixture_dir: Path = FIXTURE_DIR
) -> tuple[dict, tuple[SeedRow, ...]]:
    manifest = json.loads((fixture_dir / "manifest.json").read_text(encoding="utf-8"))
    rows: list[SeedRow] = []
    for item in _csv_rows(fixture_dir / "inventory.csv"):
        location_key = item["location_code"]
        product_key = item["product_name"]
        sku = item["sku"]
        rows.append(
            SeedRow(
                product_id=_stable_id(workspace_id, "product", product_key),
                variant_id=_stable_id(workspace_id, "variant", sku),
                balance_id=_stable_id(
                    workspace_id, "balance", f"{sku}:{location_key}"
                ),
                location_id=_stable_id(workspace_id, "location", location_key),
                product_name=product_key,
                variant_name=item["variant_name"],
                sku=sku,
                location_code=location_key,
                location_name=item["location_name"],
                quantity=int(item["quantity"]),
                low_stock_threshold=int(item["low_stock_threshold"]),
                options=json.loads(item["variant_options"] or "{}"),
                base_price_minor=(
                    int(Decimal(item["base_price_bdt"]) * 100)
                    if item["base_price_bdt"]
                    else None
                ),
                record_version=int(item["expected_record_version"] or "1"),
            )
        )
    return manifest, tuple(rows)


def _configuration() -> tuple[str, UUID]:
    values = dotenv_values(ENV_PATH)
    admin_url = (values.get(MIGRATION_KEY) or "").strip()
    workspace_text = (values.get(WORKSPACE_ID_KEY) or "").strip()
    parsed = urlsplit(admin_url.replace("postgresql+psycopg://", "postgresql://", 1))
    query = parse_qs(parsed.query)
    if not admin_url.startswith("postgresql+psycopg://"):
        raise RuntimeError("Migration URL must use postgresql+psycopg.")
    if not parsed.hostname or not parsed.hostname.endswith(".pooler.supabase.com"):
        raise RuntimeError("Migration URL must use the Supabase session pooler.")
    if parsed.port != 5432 or not (parsed.username or "").startswith("postgres."):
        raise RuntimeError("Migration URL has an invalid session pooler account.")
    if query.get("sslmode") != ["require"]:
        raise RuntimeError("Migration URL must require TLS.")
    try:
        workspace_id = UUID(workspace_text)
    except (TypeError, ValueError, AttributeError) as error:
        raise RuntimeError("Staging workspace ID is invalid.") from error
    return admin_url.replace("postgresql+psycopg://", "postgresql://", 1), workspace_id


def _remove_migration_credential() -> None:
    if not ENV_PATH.exists():
        return
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    kept = [line for line in lines if line.split("=", 1)[0] != MIGRATION_KEY]
    ENV_PATH.write_text("\n".join(kept) + "\n", encoding="utf-8")


def _ensure_workspace(connection: psycopg.Connection, workspace_id: UUID) -> None:
    row = connection.execute(
        "SELECT display_name FROM tenants WHERE id = %s AND status = 'active'",
        (workspace_id,),
    ).fetchone()
    if row is None:
        raise RuntimeError("Configured active staging workspace was not found.")


def _reject_foreign_key_collisions(
    connection: psycopg.Connection,
    workspace_id: UUID,
    fixture_version: str,
    rows: tuple[SeedRow, ...],
) -> None:
    location_codes = sorted({row.location_code for row in rows})
    skus = sorted({row.sku for row in rows})
    collisions = connection.execute(
        """
        SELECT 'location', code FROM locations
        WHERE tenant_id = %s AND code = ANY(%s)
          AND (source_reference IS DISTINCT FROM %s OR source_version IS DISTINCT FROM %s)
        UNION ALL
        SELECT 'variant', sku FROM product_variants
        WHERE tenant_id = %s AND sku = ANY(%s)
          AND (source_reference IS DISTINCT FROM %s OR source_version IS DISTINCT FROM %s)
        """,
        (
            workspace_id,
            location_codes,
            SOURCE_REFERENCE,
            fixture_version,
            workspace_id,
            skus,
            SOURCE_REFERENCE,
            fixture_version,
        ),
    ).fetchall()
    if collisions:
        kinds = ", ".join(sorted(f"{kind}:{key}" for kind, key in collisions))
        raise RuntimeError(f"Seed keys collide with unrelated workspace data: {kinds}")


def seed_inventory(
    connection: psycopg.Connection,
    workspace_id: UUID,
    manifest: dict,
    rows: tuple[SeedRow, ...],
) -> dict[str, int]:
    fixture_version = manifest["fixture_version"]
    observed_at = datetime.fromisoformat(
        f"{manifest['reference_date']}T00:00:00+06:00"
    )
    _ensure_workspace(connection, workspace_id)
    _reject_foreign_key_collisions(
        connection, workspace_id, fixture_version, rows
    )

    for row in rows:
        connection.execute(
            """
            INSERT INTO locations
                (id, tenant_id, code, name, source_kind, source_reference,
                 source_version, observed_at)
            VALUES (%s, %s, %s, %s, 'csv_snapshot', %s, %s, %s)
            ON CONFLICT (tenant_id, code) DO UPDATE
            SET name = EXCLUDED.name,
                active = TRUE,
                source_kind = EXCLUDED.source_kind,
                source_reference = EXCLUDED.source_reference,
                source_version = EXCLUDED.source_version,
                observed_at = EXCLUDED.observed_at,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                row.location_id,
                workspace_id,
                row.location_code,
                row.location_name,
                SOURCE_REFERENCE,
                fixture_version,
                observed_at,
            ),
        )
        connection.execute(
            """
            INSERT INTO products
                (id, tenant_id, name, active, source_kind, source_reference,
                 source_version, observed_at)
            VALUES (%s, %s, %s, TRUE, 'csv_snapshot', %s, %s, %s)
            ON CONFLICT (id) DO UPDATE
            SET name = EXCLUDED.name,
                active = TRUE,
                source_kind = EXCLUDED.source_kind,
                source_reference = EXCLUDED.source_reference,
                source_version = EXCLUDED.source_version,
                observed_at = EXCLUDED.observed_at,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                row.product_id,
                workspace_id,
                row.product_name,
                SOURCE_REFERENCE,
                fixture_version,
                observed_at,
            ),
        )
        connection.execute(
            """
            INSERT INTO product_variants
                (id, tenant_id, product_id, sku, name, options, base_price_minor,
                 currency, active, source_kind, source_reference, source_version,
                 observed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'BDT', TRUE,
                    'csv_snapshot', %s, %s, %s)
            ON CONFLICT (tenant_id, sku) DO UPDATE
            SET product_id = EXCLUDED.product_id,
                name = EXCLUDED.name,
                options = EXCLUDED.options,
                base_price_minor = EXCLUDED.base_price_minor,
                currency = EXCLUDED.currency,
                active = TRUE,
                source_kind = EXCLUDED.source_kind,
                source_reference = EXCLUDED.source_reference,
                source_version = EXCLUDED.source_version,
                observed_at = EXCLUDED.observed_at,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                row.variant_id,
                workspace_id,
                row.product_id,
                row.sku,
                row.variant_name,
                json.dumps(row.options),
                row.base_price_minor,
                SOURCE_REFERENCE,
                fixture_version,
                observed_at,
            ),
        )
        connection.execute(
            """
            INSERT INTO inventory_balances
                (id, tenant_id, variant_id, location_id, quantity,
                 low_stock_threshold, record_version, source_kind,
                 source_reference, source_version, observed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'csv_snapshot', %s, %s, %s)
            ON CONFLICT (tenant_id, variant_id, location_id) DO UPDATE
            SET quantity = EXCLUDED.quantity,
                low_stock_threshold = EXCLUDED.low_stock_threshold,
                record_version = CASE
                    WHEN inventory_balances.quantity = EXCLUDED.quantity
                     AND inventory_balances.low_stock_threshold = EXCLUDED.low_stock_threshold
                    THEN inventory_balances.record_version
                    ELSE inventory_balances.record_version + 1
                END,
                source_kind = EXCLUDED.source_kind,
                source_reference = EXCLUDED.source_reference,
                source_version = EXCLUDED.source_version,
                observed_at = EXCLUDED.observed_at,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                row.balance_id,
                workspace_id,
                row.variant_id,
                row.location_id,
                row.quantity,
                row.low_stock_threshold,
                row.record_version,
                SOURCE_REFERENCE,
                fixture_version,
                observed_at,
            ),
        )
    return verify_inventory(connection, workspace_id, fixture_version)


def verify_inventory(
    connection: psycopg.Connection, workspace_id: UUID, fixture_version: str
) -> dict[str, int]:
    row = connection.execute(
        """
        SELECT COUNT(*) AS variants,
               COUNT(*) FILTER (WHERE balance.quantity <= balance.low_stock_threshold)
                   AS low_stock,
               COUNT(*) FILTER (WHERE balance.quantity = 0) AS out_of_stock
        FROM inventory_balances AS balance
        JOIN product_variants AS variant
          ON variant.tenant_id = balance.tenant_id
         AND variant.id = balance.variant_id
        WHERE balance.tenant_id = %s
          AND balance.source_reference = %s
          AND balance.source_version = %s
        """,
        (workspace_id, SOURCE_REFERENCE, fixture_version),
    ).fetchone()
    return {
        "variants": row[0],
        "low_stock": row[1],
        "out_of_stock": row[2],
    }


def assert_reviewed_counts(result: dict[str, int], fixture_dir: Path = FIXTURE_DIR) -> None:
    expected = json.loads(
        (fixture_dir / "expected-results.json").read_text(encoding="utf-8")
    )["inventory"]
    reviewed = {
        "variants": expected["variants"],
        "low_stock": expected["low_stock_including_out_of_stock"],
        "out_of_stock": expected["out_of_stock"],
    }
    if result != reviewed:
        raise RuntimeError("Database inventory counts do not match reviewed fixtures.")


def reset_inventory(
    connection: psycopg.Connection, workspace_id: UUID, fixture_version: str
) -> dict[str, int]:
    movement_count = connection.execute(
        """
        SELECT COUNT(*) FROM inventory_movements AS movement
        JOIN inventory_balances AS balance
          ON balance.tenant_id = movement.tenant_id
         AND balance.id = movement.balance_id
        WHERE balance.tenant_id = %s
          AND balance.source_reference = %s
          AND balance.source_version = %s
        """,
        (workspace_id, SOURCE_REFERENCE, fixture_version),
    ).fetchone()[0]
    if movement_count:
        raise RuntimeError("Reset refused because fixture balances have movement history.")
    deleted: dict[str, int] = {}
    for name, statement in (
        (
            "balances",
            (
                "DELETE FROM inventory_balances WHERE tenant_id = %s "
                "AND source_reference = %s AND source_version = %s"
            ),
        ),
        (
            "variants",
            (
                "DELETE FROM product_variants WHERE tenant_id = %s "
                "AND source_reference = %s AND source_version = %s"
            ),
        ),
        (
            "products",
            (
                "DELETE FROM products WHERE tenant_id = %s "
                "AND source_reference = %s AND source_version = %s"
            ),
        ),
        (
            "locations",
            (
                "DELETE FROM locations WHERE tenant_id = %s "
                "AND source_reference = %s AND source_version = %s"
            ),
        ),
    ):
        cursor = connection.execute(
            statement, (workspace_id, SOURCE_REFERENCE, fixture_version)
        )
        deleted[name] = cursor.rowcount
    return deleted


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage the tenant-scoped November demo inventory seed."
    )
    parser.add_argument(
        "--action",
        choices=("plan", "apply", "execute", "verify", "reset"),
        default="plan",
    )
    parser.add_argument(
        "--confirm-workspace",
        help="Required for reset; must exactly match BIZPILOT_WORKSPACE_ID.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    stage = "configuration"
    remove_credential = False
    try:
        connection_url, workspace_id = _configuration()
        remove_credential = True
        manifest, rows = load_seed_rows(workspace_id)
        fixture_version = manifest["fixture_version"]
        if args.action == "reset" and args.confirm_workspace != str(workspace_id):
            raise RuntimeError("Reset requires the exact configured workspace ID.")
        stage = args.action
        with psycopg.connect(connection_url, connect_timeout=10) as connection:
            if args.action in {"plan", "apply"}:
                result = seed_inventory(connection, workspace_id, manifest, rows)
                assert_reviewed_counts(result)
                if args.action == "plan":
                    connection.rollback()
                else:
                    connection.commit()
            elif args.action == "execute":
                planned = seed_inventory(connection, workspace_id, manifest, rows)
                assert_reviewed_counts(planned)
                connection.rollback()
                applied = seed_inventory(connection, workspace_id, manifest, rows)
                assert_reviewed_counts(applied)
                connection.commit()
                result = {"planned": planned, "applied": applied}
            elif args.action == "verify":
                result = verify_inventory(connection, workspace_id, fixture_version)
                assert_reviewed_counts(result)
                connection.rollback()
            else:
                result = reset_inventory(connection, workspace_id, fixture_version)
                connection.commit()
    except Exception as error:  # noqa: BLE001 - suppress raw driver/config errors
        sqlstate = getattr(error, "sqlstate", None)
        print(f"November demo inventory {stage} failed.")
        if sqlstate:
            print(f"PostgreSQL SQLSTATE: {sqlstate}")
        print(str(error) if isinstance(error, RuntimeError) else "Raw error suppressed.")
        return 1
    finally:
        if remove_credential:
            _remove_migration_credential()

    print(f"November demo inventory {args.action} completed: {json.dumps(result)}")
    print(f"Database changes committed: {args.action in {'apply', 'execute', 'reset'}}")
    print("Migration credential removed from .env: True")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

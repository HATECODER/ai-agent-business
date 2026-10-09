"""Create the synthetic staging workspace and remove the admin credential."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from dotenv import dotenv_values
import psycopg


ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
MIGRATION_KEY = "BIZPILOT_MIGRATION_DATABASE_URL"
WORKSPACE_ID_KEY = "BIZPILOT_WORKSPACE_ID"
WORKSPACE_NAME_KEY = "BIZPILOT_WORKSPACE_NAME"
WORKSPACE_SLUG = "bizpilot-staging-merchant"
WORKSPACE_NAME = "BizPilot Staging Merchant"


def _write_configuration(workspace_id: str) -> None:
    values = {
        WORKSPACE_ID_KEY: workspace_id,
        WORKSPACE_NAME_KEY: WORKSPACE_NAME,
    }
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    updated: list[str] = []
    seen: set[str] = set()
    for line in lines:
        key = line.split("=", 1)[0] if "=" in line else ""
        if key == MIGRATION_KEY:
            continue
        if key in values:
            if key not in seen:
                updated.append(f"{key}={values[key]}")
                seen.add(key)
            continue
        updated.append(line)
    for key, value in values.items():
        if key not in seen:
            updated.append(f"{key}={value}")
    ENV_PATH.write_text("\n".join(updated) + "\n", encoding="utf-8")


def main() -> int:
    admin_url = (dotenv_values(ENV_PATH).get(MIGRATION_KEY) or "").strip()
    if not admin_url:
        print("Migration database URL is missing. No changes made.")
        return 1
    connection_url = admin_url.replace("postgresql+psycopg://", "postgresql://", 1)
    try:
        with psycopg.connect(connection_url, autocommit=True, connect_timeout=10) as connection:
            row = connection.execute(
                """
                INSERT INTO tenants (id, slug, display_name, timezone, currency, language)
                VALUES (%s, %s, %s, 'Asia/Dhaka', 'BDT', 'bn')
                ON CONFLICT (slug) DO UPDATE
                SET display_name = EXCLUDED.display_name,
                    timezone = EXCLUDED.timezone,
                    currency = EXCLUDED.currency,
                    language = EXCLUDED.language,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
                """,
                (uuid4(), WORKSPACE_SLUG, WORKSPACE_NAME),
            ).fetchone()
        _write_configuration(str(row[0]))
    except Exception:
        print("Workspace provisioning failed. Raw error suppressed to protect credentials.")
        return 1
    print("Synthetic staging workspace configured.")
    print("Migration credential removed from .env: True")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

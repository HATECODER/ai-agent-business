"""Invalidate tokens issued before now for the configured staging identity."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from dotenv import dotenv_values
import psycopg


ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
MIGRATION_KEY = "BIZPILOT_MIGRATION_DATABASE_URL"


def _remove_migration_credential() -> None:
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    kept = [line for line in lines if line.split("=", 1)[0] != MIGRATION_KEY]
    ENV_PATH.write_text("\n".join(kept) + "\n", encoding="utf-8")


def main() -> int:
    values = dotenv_values(ENV_PATH)
    admin_url = (values.get(MIGRATION_KEY) or "").strip()
    issuer = (values.get("BIZPILOT_OIDC_ISSUER") or "").strip()
    subject = (values.get("BIZPILOT_STAGING_OWNER_SUBJECT") or "").strip()
    parsed = urlsplit(admin_url.replace("postgresql+psycopg://", "postgresql://", 1))
    query = parse_qs(parsed.query)
    if (
        not admin_url.startswith("postgresql+psycopg://")
        or not parsed.hostname
        or not parsed.hostname.endswith(".pooler.supabase.com")
        or parsed.port != 5432
        or not (parsed.username or "").startswith("postgres.")
        or query.get("sslmode") != ["require"]
        or not issuer
        or not subject
    ):
        print("Session invalidation configuration is incomplete or unsafe.")
        return 1

    connection_url = admin_url.replace("postgresql+psycopg://", "postgresql://", 1)
    # A small positive margin avoids accepting a token minted concurrently with
    # the incident response. The tester must authenticate again afterward.
    cutoff = datetime.now(timezone.utc) + timedelta(seconds=5)
    try:
        with psycopg.connect(connection_url, connect_timeout=10) as connection:
            result = connection.execute(
                """
                UPDATE identities
                SET tokens_valid_after = %s
                WHERE issuer = %s AND subject = %s AND status = 'active'
                """,
                (cutoff, issuer, subject),
            )
            if result.rowcount != 1:
                raise RuntimeError("Expected staging identity was not updated.")
        _remove_migration_credential()
    except Exception:
        print("Staging session invalidation failed. Raw error suppressed.")
        return 1

    print("Previously issued staging identity tokens invalidated.")
    print("Migration credential removed from .env: True")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

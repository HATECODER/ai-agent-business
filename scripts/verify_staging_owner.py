"""Verify staging Owner resolution through the restricted authenticator login."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from dotenv import dotenv_values
from sqlalchemy import create_engine, text


ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"


def main() -> int:
    values = dotenv_values(ENV_PATH)
    try:
        database_url = (values.get("BIZPILOT_AUTH_DATABASE_URL") or "").strip()
        workspace_id = UUID((values.get("BIZPILOT_WORKSPACE_ID") or "").strip())
        issuer = (values.get("BIZPILOT_OIDC_ISSUER") or "").strip()
        subject = (values.get("BIZPILOT_STAGING_OWNER_SUBJECT") or "").strip()
        if not database_url or not issuer or not subject:
            raise RuntimeError("Staging verification configuration is incomplete.")
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            hide_parameters=True,
            connect_args={"connect_timeout": 10},
        )
        try:
            with engine.begin() as connection:
                connection.execute(text("SET LOCAL ROLE bizpilot_authenticator"))
                row = connection.execute(
                    text("""
                        SELECT role
                        FROM bizpilot_resolve_membership(
                            :issuer, :subject, :tenant_id, :token_issued_at
                        )
                    """),
                    {
                        "issuer": issuer,
                        "subject": subject,
                        "tenant_id": workspace_id,
                        "token_issued_at": datetime.now(timezone.utc),
                    },
                ).one_or_none()
        finally:
            engine.dispose()
        if row is None or row[0] != "owner":
            raise RuntimeError("Configured identity did not resolve as staging Owner.")
    except Exception:
        print("Restricted staging Owner verification failed. Raw error suppressed.")
        return 1
    print("Restricted staging Owner verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

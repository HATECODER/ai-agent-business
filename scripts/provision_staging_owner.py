"""Provision the approved Auth0 identity as the synthetic staging owner."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from uuid import UUID, uuid4

from dotenv import dotenv_values
import psycopg


ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
MIGRATION_KEY = "BIZPILOT_MIGRATION_DATABASE_URL"
WORKSPACE_ID_KEY = "BIZPILOT_WORKSPACE_ID"
OWNER_SUBJECT_KEY = "BIZPILOT_STAGING_OWNER_SUBJECT"
OIDC_ISSUER_KEY = "BIZPILOT_OIDC_ISSUER"


def _required_configuration() -> tuple[str, UUID, str, str]:
    values = dotenv_values(ENV_PATH)
    admin_url = (values.get(MIGRATION_KEY) or "").strip()
    workspace_text = (values.get(WORKSPACE_ID_KEY) or "").strip()
    subject = (values.get(OWNER_SUBJECT_KEY) or "").strip()
    issuer = (values.get(OIDC_ISSUER_KEY) or "").strip()

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
    if not subject or len(subject) > 255 or any(ord(character) < 32 for character in subject):
        raise RuntimeError("Staging owner subject is invalid.")
    issuer_url = urlsplit(issuer)
    if (
        issuer_url.scheme != "https"
        or not issuer_url.hostname
        or issuer_url.username
        or issuer_url.password
        or issuer_url.query
        or issuer_url.fragment
        or len(issuer) > 512
    ):
        raise RuntimeError("OIDC issuer is invalid.")
    return admin_url, workspace_id, issuer, subject


def _remove_migration_credential() -> None:
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    kept = [line for line in lines if line.split("=", 1)[0] != MIGRATION_KEY]
    ENV_PATH.write_text("\n".join(kept) + "\n", encoding="utf-8")


def main() -> int:
    stage = "configuration"
    try:
        admin_url, workspace_id, issuer, subject = _required_configuration()
        connection_url = admin_url.replace("postgresql+psycopg://", "postgresql://", 1)
        stage = "identity and membership provisioning"
        with psycopg.connect(connection_url, connect_timeout=10) as connection:
            tenant_exists = connection.execute(
                "SELECT EXISTS (SELECT 1 FROM tenants WHERE id = %s AND status = 'active')",
                (workspace_id,),
            ).fetchone()[0]
            if not tenant_exists:
                raise RuntimeError("Configured staging workspace is unavailable.")

            identity = connection.execute(
                """
                INSERT INTO identities (id, issuer, subject, display_name, status)
                VALUES (%s, %s, %s, 'Staging Project Owner', 'active')
                ON CONFLICT (issuer, subject) DO UPDATE
                SET display_name = EXCLUDED.display_name,
                    status = 'active'
                RETURNING id
                """,
                (uuid4(), issuer, subject),
            ).fetchone()
            connection.execute(
                """
                INSERT INTO memberships (id, tenant_id, identity_id, role, status)
                VALUES (%s, %s, %s, 'owner', 'active')
                ON CONFLICT (tenant_id, identity_id) DO UPDATE
                SET role = 'owner',
                    status = 'active',
                    permission_version = memberships.permission_version + 1,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (uuid4(), workspace_id, identity[0]),
            )
        _remove_migration_credential()
    except Exception as error:
        sqlstate = getattr(error, "sqlstate", None)
        print(f"Staging owner provisioning failed during {stage}.")
        if sqlstate:
            print(f"PostgreSQL SQLSTATE: {sqlstate}")
        print("Raw error suppressed to protect credentials and identity values.")
        return 1

    print("Synthetic staging Owner identity and membership configured.")
    print("Migration credential removed from .env: True")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

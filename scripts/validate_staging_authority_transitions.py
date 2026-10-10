"""Validate immediate membership revocation and role changes in HTTPS staging."""

from __future__ import annotations

import os
from pathlib import Path
# Fixed local Playwright command; no untrusted command or argument is accepted.
import subprocess  # nosec B404
from urllib.parse import parse_qs, urlsplit
from uuid import UUID

from dotenv import dotenv_values
import psycopg


ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "apps" / "web"
ENV_PATH = ROOT / ".env"
MIGRATION_KEY = "BIZPILOT_MIGRATION_DATABASE_URL"
BASE_URL = "https://bizpilot-hatecoder-staging-web.onrender.com"


def _configuration() -> tuple[str, UUID, str, str]:
    values = dotenv_values(ENV_PATH)
    admin_url = (values.get(MIGRATION_KEY) or "").strip()
    workspace_id = UUID((values.get("BIZPILOT_WORKSPACE_ID") or "").strip())
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
    ):
        raise RuntimeError("Migration URL is not an approved Supabase session pooler URL.")
    if not issuer or not subject:
        raise RuntimeError("Staging identity configuration is incomplete.")
    return admin_url.replace("postgresql+psycopg://", "postgresql://", 1), workspace_id, issuer, subject


def _set_authority(
    connection_url: str,
    workspace_id: UUID,
    issuer: str,
    subject: str,
    *,
    role: str,
    status: str,
) -> None:
    if role not in {"owner", "viewer"} or status not in {"active", "revoked"}:
        raise RuntimeError("Unsupported staging authority transition.")
    with psycopg.connect(connection_url, connect_timeout=10) as connection:
        result = connection.execute(
            """
            UPDATE memberships AS membership
            SET role = %s,
                status = %s,
                permission_version = permission_version + 1,
                updated_at = CURRENT_TIMESTAMP
            FROM identities AS identity
            WHERE membership.identity_id = identity.id
              AND membership.tenant_id = %s
              AND identity.issuer = %s
              AND identity.subject = %s
            """,
            (role, status, workspace_id, issuer, subject),
        )
        if result.rowcount != 1:
            raise RuntimeError("Expected staging membership was not updated.")


def _run_browser_check(expected_state: str) -> None:
    environment = os.environ.copy()
    environment["BIZPILOT_BROWSER_BASE_URL"] = BASE_URL
    environment["BIZPILOT_EXPECTED_AUTHORITY_STATE"] = expected_state
    npm = "npm.cmd" if os.name == "nt" else "npm"
    # Fixed argv and shell=False prevent command interpretation.
    subprocess.run(  # nosec B603
        [npm, "exec", "playwright", "test", "e2e/authority-transitions.spec.ts"],
        cwd=WEB_ROOT,
        env=environment,
        check=True,
    )


def _remove_migration_credential() -> None:
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    kept = [line for line in lines if line.split("=", 1)[0] != MIGRATION_KEY]
    ENV_PATH.write_text("\n".join(kept) + "\n", encoding="utf-8")


def main() -> int:
    restored = False
    try:
        connection_url, workspace_id, issuer, subject = _configuration()
        try:
            _set_authority(
                connection_url, workspace_id, issuer, subject, role="owner", status="revoked"
            )
            _run_browser_check("revoked")
            print("Immediate membership revocation check passed.")

            _set_authority(
                connection_url, workspace_id, issuer, subject, role="viewer", status="active"
            )
            _run_browser_check("viewer")
            print("Immediate role-change check passed.")
        finally:
            _set_authority(
                connection_url, workspace_id, issuer, subject, role="owner", status="active"
            )
            restored = True
            _remove_migration_credential()
        _run_browser_check("owner")
    except Exception:
        print("Staging authority transition validation failed. Raw error suppressed.")
        print(f"Owner authority restored: {restored}")
        return 1
    print("Owner authority restored: True")
    print("Migration credential removed from .env: True")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

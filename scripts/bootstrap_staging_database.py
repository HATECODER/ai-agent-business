"""Bootstrap the approved Supabase staging database without exposing secrets."""

from __future__ import annotations

import secrets
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from alembic import command
from alembic.config import Config
from dotenv import dotenv_values
import psycopg
from psycopg import sql
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
MIGRATION_KEY = "BIZPILOT_MIGRATION_DATABASE_URL"
RUNTIME_KEY = "BIZPILOT_DATABASE_URL"
AUTH_KEY = "BIZPILOT_AUTH_DATABASE_URL"


def _migration_url() -> str:
    value = (dotenv_values(ENV_PATH).get(MIGRATION_KEY) or "").strip()
    parsed = urlsplit(value.replace("postgresql+psycopg://", "postgresql://", 1))
    query = parse_qs(parsed.query)
    if not value.startswith("postgresql+psycopg://"):
        raise RuntimeError("Migration URL must use postgresql+psycopg.")
    if not parsed.hostname or not parsed.hostname.endswith(".pooler.supabase.com"):
        raise RuntimeError("Migration URL must use the Supabase session pooler.")
    if parsed.port != 5432 or not (parsed.username or "").startswith("postgres."):
        raise RuntimeError("Migration URL has an invalid session pooler account.")
    if query.get("sslmode") != ["require"]:
        raise RuntimeError("Migration URL must require TLS.")
    return value


def _psycopg_url(url: str) -> str:
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


def _provision_login(connection: psycopg.Connection, login: str, granted_role: str, password: str) -> None:
    exists = connection.execute(
        "SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = %s)", (login,)
    ).fetchone()[0]
    identifier = sql.Identifier(login)
    password_literal = sql.Literal(password)
    if exists:
        connection.execute(
            sql.SQL("ALTER ROLE {} WITH LOGIN PASSWORD {}").format(identifier, password_literal)
        )
    else:
        connection.execute(
            sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(identifier, password_literal)
        )
    connection.execute(
        sql.SQL(
            "ALTER ROLE {} NOCREATEDB NOCREATEROLE NOINHERIT CONNECTION LIMIT 10"
        ).format(identifier)
    )
    connection.execute(
        sql.SQL("GRANT {} TO {}").format(sql.Identifier(granted_role), identifier)
    )


def _verify_role_flags(connection: psycopg.Connection, role_names: tuple[str, ...]) -> None:
    rows = connection.execute(
        """
        SELECT rolname, rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls
        FROM pg_roles
        WHERE rolname = ANY(%s)
        """,
        (list(role_names),),
    ).fetchall()
    if len(rows) != len(role_names):
        raise RuntimeError("A required restricted role is missing.")
    if any(any(row[index] for index in range(1, 6)) for row in rows):
        raise RuntimeError("A database role has an elevated attribute.")


def _restricted_url(admin_url: str, role_name: str, password: str) -> str:
    parsed = make_url(admin_url)
    admin_username = parsed.username or ""
    if not admin_username.startswith("postgres."):
        raise RuntimeError("Cannot derive the Supabase project-qualified login.")
    project_suffix = admin_username[len("postgres") :]
    return parsed.set(
        username=f"{role_name}{project_suffix}", password=password
    ).render_as_string(hide_password=False)


def _write_runtime_urls(runtime_url: str, auth_url: str) -> None:
    values = {RUNTIME_KEY: runtime_url, AUTH_KEY: auth_url}
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


def _verify_restricted_url(url: str, role: str) -> None:
    if role not in {"bizpilot_runtime", "bizpilot_authenticator"}:
        raise RuntimeError("Unexpected restricted database role.")
    engine = create_engine(
        url, pool_pre_ping=True, hide_parameters=True, connect_args={"connect_timeout": 10}
    )
    try:
        with engine.begin() as connection:
            connection.execute(text(f"SET LOCAL ROLE {role}"))
            if connection.execute(text("SELECT 1")).scalar_one() != 1:
                raise RuntimeError("Restricted database login verification failed.")
    finally:
        engine.dispose()


def main() -> int:
    stage = "configuration"
    try:
        admin_url = _migration_url()
        roles_sql = (ROOT / "backend" / "sql" / "roles.sql").read_text(encoding="utf-8")
        stage = "base roles"
        with psycopg.connect(_psycopg_url(admin_url), autocommit=True, connect_timeout=10) as connection:
            connection.execute(roles_sql)
            _verify_role_flags(
                connection,
                ("bizpilot_runtime", "bizpilot_worker", "bizpilot_authenticator"),
            )

        stage = "schema migrations"
        config = Config(str(ROOT / "backend" / "alembic.ini"))
        config.set_main_option("sqlalchemy.url", admin_url.replace("%", "%%"))
        command.upgrade(config, "head")

        runtime_password = secrets.token_urlsafe(48)
        auth_password = secrets.token_urlsafe(48)
        stage = "restricted logins"
        with psycopg.connect(_psycopg_url(admin_url), autocommit=True, connect_timeout=10) as connection:
            _provision_login(connection, "bizpilot_api_login", "bizpilot_runtime", runtime_password)
            _provision_login(
                connection,
                "bizpilot_auth_login",
                "bizpilot_authenticator",
                auth_password,
            )
            _verify_role_flags(connection, ("bizpilot_api_login", "bizpilot_auth_login"))

        runtime_url = _restricted_url(admin_url, "bizpilot_api_login", runtime_password)
        auth_url = _restricted_url(admin_url, "bizpilot_auth_login", auth_password)
        stage = "restricted login verification"
        _verify_restricted_url(runtime_url, "bizpilot_runtime")
        _verify_restricted_url(auth_url, "bizpilot_authenticator")
        stage = "local configuration"
        _write_runtime_urls(runtime_url, auth_url)
    except Exception as error:
        sqlstate = getattr(error, "sqlstate", None)
        print(f"Staging database bootstrap failed during {stage}.")
        if sqlstate:
            print(f"PostgreSQL SQLSTATE: {sqlstate}")
        print("Raw error suppressed to protect credentials.")
        return 1

    print("Staging migrations and restricted database logins configured.")
    print("Migration credential removed from .env: True")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

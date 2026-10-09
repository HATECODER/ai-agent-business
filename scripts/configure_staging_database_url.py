"""Safely configure the temporary Supabase migration connection URL."""

from __future__ import annotations

import getpass
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit


ENV_KEY = "BIZPILOT_MIGRATION_DATABASE_URL"
PASSWORD_MARKERS = ("[YOUR-PASSWORD]", "[YOUR_PASSWORD]")


def _build_url(template: str, password: str) -> str:
    normalized = template.strip().replace("postgresql://", "postgresql+psycopg://", 1)
    marker = next((item for item in PASSWORD_MARKERS if item in normalized), None)
    if marker is None:
        raise ValueError("Use the Supabase URI template containing [YOUR-PASSWORD].")

    normalized = normalized.replace(marker, quote(password, safe=""), 1)
    parsed = urlsplit(normalized)
    if parsed.scheme != "postgresql+psycopg":
        raise ValueError("The URI must use the PostgreSQL scheme.")
    if not parsed.hostname or not parsed.hostname.endswith(".pooler.supabase.com"):
        raise ValueError("Choose the Supabase Session pooler URI.")
    if parsed.port != 5432:
        raise ValueError("Session pooler must use port 5432.")
    if not parsed.username or not parsed.username.startswith("postgres."):
        raise ValueError("The Session pooler username must start with postgres.")
    if parsed.path != "/postgres":
        raise ValueError("The expected staging database name is postgres.")

    query = parsed.query
    if "sslmode=" not in query:
        query = f"{query}&sslmode=require" if query else "sslmode=require"
    elif "sslmode=require" not in query.split("&"):
        raise ValueError("The connection must use sslmode=require.")
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, query, ""))


def _write_env(path: Path, url: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    replacement = f"{ENV_KEY}={url}"
    updated: list[str] = []
    replaced = False
    for line in lines:
        if line.startswith(f"{ENV_KEY}="):
            if not replaced:
                updated.append(replacement)
                replaced = True
        else:
            updated.append(line)
    if not replaced:
        updated.append(replacement)
    path.write_text("\n".join(updated) + "\n", encoding="utf-8")


def main() -> int:
    print("Paste the Supabase Session pooler URI template with [YOUR-PASSWORD].")
    template = input("URI template: ").strip()
    password = getpass.getpass("Database password (hidden): ")
    if not password:
        print("Database password is required. No changes made.")
        return 1
    try:
        url = _build_url(template, password)
        _write_env(Path(__file__).resolve().parents[1] / ".env", url)
    except ValueError as exc:
        print(f"Configuration rejected: {exc}")
        return 1
    print(f"{ENV_KEY} configured without displaying the credential.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

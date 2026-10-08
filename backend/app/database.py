"""PostgreSQL engine and transaction-scoped tenant context."""

from collections.abc import Iterator
from contextlib import contextmanager
import os
from uuid import UUID

from sqlalchemy import Connection, Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from backend.app.authorization import TenantAuthority


def database_url() -> str:
    value = os.getenv("BIZPILOT_DATABASE_URL", "").strip()
    if not value:
        raise RuntimeError("BIZPILOT_DATABASE_URL is required for the commercial backend.")
    if not value.startswith(("postgresql://", "postgresql+psycopg://")):
        raise RuntimeError("The commercial backend requires PostgreSQL.")
    return value


def create_database_engine(url: str | None = None) -> Engine:
    try:
        return create_engine(
            url or database_url(),
            pool_pre_ping=True,
            hide_parameters=True,
            future=True,
        )
    except (SQLAlchemyError, ValueError) as error:
        raise RuntimeError("Database configuration is invalid.") from error


@contextmanager
def tenant_transaction(engine: Engine, authority: TenantAuthority) -> Iterator[Connection]:
    """Open one transaction with local RLS identity and tenant settings.

    The production engine must authenticate as the restricted runtime login
    that inherits or can SET ROLE to ``bizpilot_runtime``. Context is local to
    this transaction, preventing values from leaking through a pooled
    connection.
    """
    if authority.permission_version < 1:
        raise ValueError("Invalid tenant authority.")
    try:
        UUID(authority.tenant_id)
        UUID(authority.identity_id)
        UUID(authority.membership_id)
    except (ValueError, AttributeError) as error:
        raise ValueError("Invalid tenant authority.") from error

    settings = {
        "tenant_id": authority.tenant_id,
        "identity_id": authority.identity_id,
        "membership_id": authority.membership_id,
        "permission_version": str(authority.permission_version),
    }
    with engine.begin() as connection:
        connection.execute(text("SET LOCAL ROLE bizpilot_runtime"))
        for name, value in settings.items():
            connection.execute(
                text("SELECT set_config(:name, :value, true)"),
                {"name": f"app.{name}", "value": value},
            )
        yield connection

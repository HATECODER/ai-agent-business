"""Tenant-scoped, read-only inventory query service."""

from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError

from backend.app.authorization import TenantAuthority
from backend.app.database import tenant_transaction


class InventoryUnavailable(RuntimeError):
    """Inventory could not be read without exposing infrastructure details."""


class InventoryItem(BaseModel):
    inventory_id: UUID
    product_id: UUID
    variant_id: UUID
    location_id: UUID
    product_name: str
    variant_name: str
    sku: str
    location_code: str
    location_name: str
    quantity: int
    low_stock_threshold: int
    is_low_stock: bool
    base_price_minor: int | None
    currency: str | None
    record_version: int
    source_kind: str
    source_version: str | None
    observed_at: datetime


class InventoryPage(BaseModel):
    items: list[InventoryItem]
    next_cursor: UUID | None = None
    limit: int = Field(ge=1, le=100)


InventoryReader = Callable[[TenantAuthority, int, UUID | None, bool], InventoryPage]


def database_inventory_reader(engine: Engine) -> InventoryReader:
    def read(
        authority: TenantAuthority,
        limit: int,
        after: UUID | None,
        low_stock_only: bool,
    ) -> InventoryPage:
        if not 1 <= limit <= 100:
            raise ValueError("Inventory page size is invalid.")
        try:
            with tenant_transaction(engine, authority) as connection:
                rows = connection.execute(
                    text("""
                        SELECT
                            balance.id AS inventory_id,
                            product.id AS product_id,
                            variant.id AS variant_id,
                            location.id AS location_id,
                            product.name AS product_name,
                            variant.name AS variant_name,
                            variant.sku,
                            location.code AS location_code,
                            location.name AS location_name,
                            balance.quantity,
                            balance.low_stock_threshold,
                            balance.quantity <= balance.low_stock_threshold AS is_low_stock,
                            variant.base_price_minor,
                            variant.currency,
                            balance.record_version,
                            balance.source_kind,
                            balance.source_version,
                            balance.observed_at
                        FROM inventory_balances AS balance
                        JOIN product_variants AS variant
                          ON variant.tenant_id = balance.tenant_id
                         AND variant.id = balance.variant_id
                        JOIN products AS product
                          ON product.tenant_id = variant.tenant_id
                         AND product.id = variant.product_id
                        JOIN locations AS location
                          ON location.tenant_id = balance.tenant_id
                         AND location.id = balance.location_id
                        WHERE balance.tenant_id = :tenant_id
                          AND (
                              CAST(:after_id AS uuid) IS NULL
                              OR balance.id > CAST(:after_id AS uuid)
                          )
                          AND (
                              NOT :low_stock_only
                              OR balance.quantity <= balance.low_stock_threshold
                          )
                          AND product.active
                          AND variant.active
                          AND location.active
                        ORDER BY balance.id
                        LIMIT :fetch_limit
                    """),
                    {
                        "tenant_id": UUID(authority.tenant_id),
                        "after_id": str(after) if after else None,
                        "low_stock_only": low_stock_only,
                        "fetch_limit": limit + 1,
                    },
                ).mappings().all()
        except (SQLAlchemyError, ValueError) as error:
            raise InventoryUnavailable("Inventory query failed.") from error

        has_next = len(rows) > limit
        visible_rows = rows[:limit]
        items = [InventoryItem.model_validate(dict(row)) for row in visible_rows]
        next_cursor = items[-1].inventory_id if has_next and items else None
        return InventoryPage(items=items, next_cursor=next_cursor, limit=limit)

    return read

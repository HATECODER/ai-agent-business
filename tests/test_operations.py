import pytest
from pydantic import ValidationError

from tools.operations import create_task, get_inventory, get_low_stock_products, get_pending_tasks


def test_low_stock_is_determined_by_threshold(seeded_db):
    items = get_low_stock_products(seeded_db)
    assert len(items) >= 2
    assert all(item["quantity"] <= item["low_stock_threshold"] for item in items)


def test_inventory_filters(seeded_db):
    items = get_inventory("Premium Cotton Polo", "XL", "black", seeded_db)
    assert len(items) == 1
    assert items[0]["quantity"] == 2
    assert get_inventory("No Such Product", db_path=seeded_db) == []


def test_task_creation_and_priority_validation(seeded_db):
    task = create_task("Call supplier", "Ask about stock", "high", "operations", db_path=seeded_db)
    assert task["created"] is True
    assert any(item["id"] == task["id"] for item in get_pending_tasks(db_path=seeded_db))
    with pytest.raises(ValidationError):
        create_task("Bad priority", "", "urgent", "operations", db_path=seeded_db)


def test_restock_task_deduplicates(seeded_db):
    item = get_low_stock_products(seeded_db)[0]
    args = ("Review restock", "Stock is low", "high", "restock", "inventory", item["inventory_id"])
    first = create_task(*args, db_path=seeded_db)
    second = create_task(*args, db_path=seeded_db)
    assert first["created"] is True
    assert second["created"] is False
    assert first["id"] == second["id"]

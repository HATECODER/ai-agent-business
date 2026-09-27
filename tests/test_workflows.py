from database.db import connect
from tools.operations import get_low_stock_products
from workflows.inventory_workflow import run_low_stock_workflow


def test_workflow_creates_once_and_is_idempotent(seeded_db):
    count = len(get_low_stock_products(seeded_db))
    first = run_low_stock_workflow(seeded_db)
    second = run_low_stock_workflow(seeded_db)
    assert first["tasks_created"] == count
    assert first["low_stock_items"] == count
    assert second["tasks_created"] == 0
    assert second["tasks_already_existing"] == count
    with connect(seeded_db) as db:
        actual = db.execute("SELECT COUNT(*) FROM tasks WHERE category = 'restock'").fetchone()[0]
    assert actual == count

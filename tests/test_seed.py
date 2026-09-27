from concurrent.futures import ThreadPoolExecutor

from database.db import connect
from database.seed import seed_database, today


def test_seed_is_safe_to_repeat_and_reset(seeded_db):
    assert seed_database(seeded_db) is False
    with connect(seeded_db) as db:
        counts = {table: db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                  for table in ("customers", "products", "inventory", "orders", "expenses", "tasks")}
        todays_orders = db.execute("SELECT COUNT(*) FROM orders WHERE order_date = ?",
                                   (today().date().isoformat(),)).fetchone()[0]
    assert counts["customers"] >= 20
    assert counts["products"] >= 10
    assert counts["inventory"] >= 10
    assert counts["orders"] >= 20
    assert counts["expenses"] >= 10
    assert counts["tasks"] >= 5
    assert todays_orders > 0
    assert seed_database(seeded_db, reset=True) is True
    with connect(seeded_db) as db:
        assert db.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == counts["customers"]


def test_concurrent_first_run_seeds_only_once(tmp_path):
    database = tmp_path / "concurrent.sqlite3"

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(lambda _: seed_database(database), range(4)))

    assert results.count(True) == 1
    assert results.count(False) == 3
    with connect(database) as db:
        assert db.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 24
        assert db.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 10
        assert db.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 28

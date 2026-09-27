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

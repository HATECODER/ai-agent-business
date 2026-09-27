"""Repeatable fictional Bangladesh commerce data for demos."""

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

from database.db import connect, initialize_database


BDT = timezone(timedelta(hours=6))


def today() -> datetime:
    return datetime.now(BDT)


def seed_database(path: str | Path | None = None, *, reset: bool = False) -> bool:
    """Seed an empty database; reset only when explicitly requested."""
    initialize_database(path)
    now = today()
    stamp = now.isoformat(timespec="seconds")
    day = now.date()
    names = [
        "Rahim Ahmed", "Sadia Islam", "Karim Hasan", "Nadia Rahman",
        "Tanvir Hossain", "Farzana Akter", "Mahir Chowdhury", "Nusrat Jahan",
        "Arif Mahmud", "Samira Khan", "Imran Kabir", "Tania Sultana",
        "Shakib Hasan", "Rima Akter", "Fahim Rahman", "Jannat Ara",
        "Rafiul Islam", "Maliha Noor", "Adnan Karim", "Sharmin Nahar",
        "Sabbir Hossain", "Ishrat Zaman", "Rashed Mia", "Labiba Ahmed",
    ]
    products = [
        ("Premium Cotton Polo", "Tops", 1450),
        ("Classic Oxford Shirt", "Shirts", 1850),
        ("Oversized T-Shirt", "Tops", 950),
        ("Denim Jeans", "Bottoms", 2350),
        ("Lightweight Hoodie", "Outerwear", 2150),
        ("Casual Sneakers", "Shoes", 3200),
        ("Formal Shirt", "Shirts", 1750),
        ("Women's Kurti", "Women", 1650),
        ("Sports T-Shirt", "Sports", 850),
        ("Chino Pants", "Bottoms", 1950),
    ]
    variants = [
        (1, "Black XL", "Black", "XL", 2, 5),
        (1, "Black L", "Black", "L", 9, 5),
        (1, "White M", "White", "M", 1, 4),
        (2, "White M", "White", "M", 3, 5),
        (2, "Blue L", "Blue", "L", 11, 5),
        (3, "Black XL", "Black", "XL", 15, 5),
        (4, "Blue 32", "Blue", "32", 7, 4),
        (5, "Grey L", "Grey", "L", 4, 4),
        (6, "White 42", "White", "42", 8, 3),
        (7, "White M", "White", "M", 12, 5),
        (8, "Red M", "Red", "M", 6, 4),
        (9, "Blue L", "Blue", "L", 13, 4),
        (10, "Khaki 32", "Khaki", "32", 5, 4),
    ]
    with connect(path) as db:
        if reset:
            for table in ("campaigns", "tasks", "expenses", "orders", "inventory", "products", "customers"):
                db.execute(f"DELETE FROM {table}")
        elif db.execute("SELECT 1 FROM customers LIMIT 1").fetchone():
            return False

        for index, name in enumerate(names, start=1):
            db.execute("""INSERT INTO customers
                (id, name, phone, preferred_language, preferred_category,
                 preferred_size, preferred_payment_method, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (index, name, f"017{index:08d}",
                 ("banglish", "bn", "en")[index % 3],
                 ("Tops", "Shirts", "Bottoms")[index % 3],
                 ("M", "L", "XL")[index % 3],
                 "COD" if index % 2 else "bKash", stamp))
        for index, (name, category, price) in enumerate(products, start=1):
            db.execute("""INSERT INTO products
                (id, name, category, description, base_price, active, created_at)
                VALUES (?, ?, ?, ?, ?, 1, ?)""",
                (index, name, category, f"Everyday {name.lower()} for local customers.", price, stamp))
        for index, (product_id, variant, color, size, quantity, threshold) in enumerate(variants, start=1):
            db.execute("""INSERT INTO inventory
                (id, product_id, variant_name, color, size, quantity, low_stock_threshold, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (index, product_id, variant, color, size, quantity, threshold, stamp))

        # First four customers are deliberately inactive. Other customers have
        # delivered orders in the last month, and today's sales include receivables.
        for index in range(1, 29):
            customer_id = ((index - 1) % 24) + 1
            age = 45 + index if customer_id <= 4 else index % 12
            order_day = day - timedelta(days=age)
            status = "delivered" if index <= 24 else ("confirmed" if index < 28 else "cancelled")
            if index >= 25:
                order_day = day
            amount = (1100 + (index % 6) * 450)
            received = amount if index % 5 else amount // 2
            if index == 26:
                received = 0
            if status == "cancelled":
                received = 0
            payment = "paid" if received == amount else ("unpaid" if received == 0 else "partial")
            db.execute("""INSERT INTO orders
                (id, customer_id, order_date, status, total_amount, payment_status,
                 amount_received, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (index, customer_id, order_day.isoformat(), status, amount, payment,
                 received, stamp))
        db.execute("""UPDATE customers SET last_purchase_at = (
            SELECT MAX(order_date) FROM orders
            WHERE orders.customer_id = customers.id AND orders.status = 'delivered')""")

        expense_categories = ["delivery", "packaging", "rent", "utilities", "supplies"]
        for index in range(1, 13):
            expense_day = day if index <= 3 else day - timedelta(days=index - 2)
            db.execute("""INSERT INTO expenses
                (id, expense_date, category, description, amount, created_at)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (index, expense_day.isoformat(), expense_categories[index % 5],
                 f"Demo {expense_categories[index % 5]} cost", 120 + index * 80, stamp))
        tasks = [
            ("Confirm COD orders", "Call customers before dispatch", "operations", "high"),
            ("Review weekly expenses", "Check expense categories", "finance", "medium"),
            ("Prepare Eid content", "Draft a seasonal content idea", "growth", "low"),
            ("Follow up open invoices", "Review outstanding receivables", "finance", "high"),
            ("Inspect returns", "Review returned items", "operations", "medium"),
        ]
        for index, (title, description, category, priority) in enumerate(tasks, start=1):
            db.execute("""INSERT INTO tasks
                (id, title, description, category, priority, status, created_at)
                VALUES (?, ?, ?, ?, ?, 'pending', ?)""",
                (index, title, description, category, priority, stamp))
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the BizPilot demo database")
    parser.add_argument("--reset", action="store_true", help="replace existing demo data")
    args = parser.parse_args()
    changed = seed_database(reset=args.reset)
    print("Demo data seeded." if changed else "Database already has data; use --reset to recreate it.")

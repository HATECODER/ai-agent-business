"""No-cost, rule-based demo replies backed by the same business tools.

This is deliberately labeled as a demo assistant, not an LLM replacement.
"""

from pathlib import Path
import re

from security.auth import ActorContext, require_owner
from services.actions import propose_action
from services.business_summary import get_business_summary
from tools.finance import get_expense_summary, get_financial_summary, get_sales_summary
from tools.growth import get_inactive_customers
from tools.operations import get_inventory, get_low_stock_products, get_pending_tasks


def _has(text: str, *phrases: str) -> bool:
    return any(phrase in text for phrase in phrases)


def _days(text: str, history: list) -> int:
    for candidate in [text, *(str(item.get("content", "")) for item in reversed(history)
                              if isinstance(item, dict) and item.get("role") == "user")]:
        match = re.search(r"\b(7|30|60)\b|([৭৩০৬০]+)\s*দিন", candidate)
        if match:
            if match.group(1):
                return int(match.group(1))
            return int(match.group(2).translate(str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")))
    return 30


def _money(value: int | float) -> str:
    return f"৳{value:,.0f}"


def offline_reply(message: str, history: list | None = None,
                  db_path: str | Path | None = None,
                  actor: ActorContext | None = None) -> tuple[str, list]:
    """Handle the defined demo intents without a network request."""
    actor = require_owner(actor)
    history = history or []
    text = message.casefold()
    wants_task = _has(text, "task", "banaw", "banao", "create", "কাজ", "টাস্ক")
    wants_stock = _has(text, "stock", "inventory", "স্টক", "মজুদ")

    if wants_stock and wants_task and _has(text, "restock", "low", "kom", "কম", "egular", "এগুল"):
        proposal = propose_action("run_restock_review", {}, actor, db_path)
        body = (f"Restock review proposal ready (ID: {proposal['id']}). "
                "Owner confirmation chara kono task ba purchase create hoyni.")
    elif _has(text, "low stock", "stock kom", "স্টক কম", "kom stock"):
        items = get_low_stock_products(db_path)
        body = ("Low-stock item nei." if not items else
                "Low-stock variants (database theke):\n" + "\n".join(
                    f"- {item['product']} {item['variant_name']}: {item['quantity']} units "
                    f"(threshold {item['low_stock_threshold']})" for item in items))
    elif wants_stock:
        colors = ("black", "white", "blue", "red", "grey", "khaki")
        color = next((part for part in colors if part in text), "")
        size = next((part for part in ("xxl", "xl", "32", "42", "l", "m")
                     if re.search(rf"(?<![a-z0-9]){part}(?![a-z0-9])", text)), "")
        product = next((part for part in ("polo", "shirt", "jeans", "hoodie", "sneakers", "kurti", "pants")
                        if part in text), "")
        items = get_inventory(product, size, color, db_path)
        body = ("Matching inventory nei." if not items else
                "Inventory (database theke):\n" + "\n".join(
                    f"- {item['product']} {item['variant_name']}: {item['quantity']} units"
                    for item in items))
    elif _has(text, "campaign", "ক্যাম্পেইন"):
        days = _days(text, history)
        customers = get_inactive_customers(days, db_path)
        payload = {
            "segment_description": (
                f"Customers with no delivered purchase in {days} days ({len(customers)} customers)"),
            "objective": "Re-engage inactive customers", "offer": None, "channel": "facebook",
        }
        proposal = propose_action("create_campaign_draft", payload, actor, db_path)
        body = (f"**Campaign draft proposal:** {proposal['id']}\n\n"
                f"Target: {payload['segment_description']}\n\n"
                "Eta pending proposal; owner confirmation chara draft save ba message send hoyni.")
    elif _has(text, "inactive", "kine nai", "keneni", "কেনেনি", "কিনে নাই", "customer gula ber", "customer dekhao"):
        days = _days(text, history)
        customers = get_inactive_customers(days, db_path)
        body = (f"{days} dine inactive customer: {len(customers)}.\n" +
                "\n".join(f"- {person['name']} (last delivered purchase: "
                          f"{person['last_purchase_date'] or 'none'})" for person in customers))
    elif _has(text, "pending task", "high priority", "baki kaj", "বাকি কাজ", "পেন্ডিং", "কাজগুলো"):
        tasks = get_pending_tasks(priority="high" if _has(text, "high priority") else "", db_path=db_path)
        body = ("Open task nei." if not tasks else "Open tasks:\n" +
                "\n".join(f"- [{task['priority']}] {task['title']}" for task in tasks))
    elif _has(text, "ki ki kora uchit", "sob miliye", "current situation", "business er", "কি কি করা উচিত", "আজ কী করব"):
        facts = get_business_summary(db_path)
        finance = facts["financial_summary"]
        body = ("**Today's priorities (recommendations):**\n"
                f"1. Review {facts['low_stock']['total_count']} low-stock variants.\n"
                f"2. Review {_money(finance['order_cohort_receivable'])} receivable "
                "on today's order cohort.\n"
                f"3. Re-engage {facts['inactive_customer_count']} inactive customers.\n"
                f"4. Review {facts['high_priority_tasks']['total_count']} high-priority open tasks.\n\n"
                "Cash flow is unavailable because payment-event dates and opening balance are not modeled.")
    elif _has(text, "financial", "cash flow", "cashflow", "receivable", "payment baki", "টাকা বাকি", "আর্থিক"):
        explicit_date = re.search(r"\b\d{4}-\d{2}-\d{2}\b", text)
        if explicit_date:
            body = ("Offline demo mode supports today's scripted financial summary only. "
                    "Use an explicit date-range API/tool in model mode after validation.")
        else:
            summary = get_financial_summary(db_path=db_path)
            body = (f"Today's order cohort: revenue {_money(summary['revenue'])}; receipts recorded on those "
                    f"orders {_money(summary['order_cohort_receipts'])}; dated expenses "
                    f"{_money(summary['dated_expenses'])}; cohort receivable "
                    f"{_money(summary['order_cohort_receivable'])}. Order count: {summary['order_count']}. "
                    "True period cash flow is unavailable because payment-event dates and opening balance are not modeled.")
    elif _has(text, "expense", "khoroch", "খরচ"):
        summary = get_expense_summary(db_path=db_path)
        body = f"Ajker expenses: {_money(summary['expenses'])} ({summary['expense_count']} entries)."
    elif _has(text, "sales", "revenue", "বিক্রি"):
        summary = get_sales_summary(db_path=db_path)
        body = (f"Ajker sales: {_money(summary['gross_sales'])} across {summary['order_count']} "
                f"confirmed/delivered orders. Receipts recorded on those orders "
                f"{_money(summary['order_cohort_receipts'])}; cohort receivable "
                f"{_money(summary['order_cohort_receivable'])}.")
    else:
        body = ("Ei offline demo inventory, low stock, tasks, inactive customers, "
                "campaign drafts, sales, expenses, finance, and daily priorities handle kore. "
                "Try: `kon product stock kom?`")

    response = "**Offline demo mode — no API call**\n\n" + body
    next_history = [*history, {"role": "user", "content": message},
                    {"role": "assistant", "content": response}]
    return response, next_history

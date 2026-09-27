from database.db import connect
from database.seed import today
from tools.growth import create_campaign_brief, get_inactive_customers


def test_inactive_customers_exclude_recent_delivered_purchases(seeded_db):
    inactive = get_inactive_customers(30, seeded_db)
    ids = {customer["customer_id"] for customer in inactive}
    assert {1, 2, 3}.issubset(ids)
    assert 5 not in ids
    assert all(customer["last_purchase_date"] is None or
               customer["last_purchase_date"] < (today().date()).isoformat()
               for customer in inactive)


def test_campaign_is_only_a_draft(seeded_db):
    brief = create_campaign_brief("30-day inactive customers", "Win back buyers", db_path=seeded_db)
    assert brief["status"] == "draft_not_sent"
    assert brief["message_bn_or_banglish"]
    with connect(seeded_db) as db:
        status = db.execute("SELECT status FROM campaigns WHERE id = ?", (brief["campaign_id"],)).fetchone()[0]
    assert status == "draft"

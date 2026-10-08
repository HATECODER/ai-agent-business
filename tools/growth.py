"""Customer segmentation and unsent draft campaigns."""

from datetime import timedelta
from pathlib import Path

from database.db import connect
from database.models import CampaignInput
from database.seed import today


def get_inactive_customers(days: int = 30, db_path: str | Path | None = None) -> list[dict]:
    if not 1 <= days <= 3650:
        raise ValueError("Days must be between 1 and 3650.")
    cutoff = (today().date() - timedelta(days=days)).isoformat()
    with connect(db_path) as db:
        return [dict(row) for row in db.execute("""SELECT c.id AS customer_id, c.name,
            MAX(CASE WHEN o.status = 'delivered' THEN o.order_date END) AS last_purchase_date,
            c.preferred_category, c.preferred_language, c.preferred_payment_method
            FROM customers c LEFT JOIN orders o ON o.customer_id = c.id
            GROUP BY c.id
            HAVING last_purchase_date IS NULL OR last_purchase_date < ?
            ORDER BY last_purchase_date, c.name""", (cutoff,))]


def create_campaign_brief(segment_description: str, objective: str,
                          offer: str | None = None, channel: str = "facebook",
                          db_path: str | Path | None = None) -> dict:
    campaign = CampaignInput(segment_description=segment_description,
                             objective=objective, offer=offer, channel=channel)
    name = f"Re-engagement — {campaign.segment_description[:55]}"
    offer_text = campaign.offer or "See the latest collection"
    with connect(db_path) as db:
        cursor = db.execute("""INSERT INTO campaigns
            (name, campaign_type, target_description, objective, offer, channel, status, created_at)
            VALUES (?, 're_engagement', ?, ?, ?, ?, 'draft', ?)""",
            (name, campaign.segment_description, campaign.objective,
             campaign.offer, campaign.channel,
             today().isoformat(timespec="seconds")))
    return {
        "campaign_id": cursor.lastrowid,
        "campaign_name": name,
        "objective": campaign.objective,
        "target_segment": campaign.segment_description,
        "suggested_offer": offer_text,
        "channel": campaign.channel,
        "status": "draft_not_sent",
        "message_en": f"We've missed you! {offer_text}. Reply to see what fits you.",
        "message_bn_or_banglish": f"Assalamu alaikum! Onek din dekha nei. {offer_text}. Pochondo hole reply din.",
        "call_to_action": "Reply for product suggestions",
    }

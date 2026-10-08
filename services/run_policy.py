"""Bound model inputs, tool outputs, concurrency, and synthetic-pilot spend."""

from dataclasses import dataclass
from datetime import timedelta
import json
from pathlib import Path
from uuid import uuid4

from config import (
    ai_mode,
    daily_budget_usd_micros,
    gemini_model_name,
    max_active_runs_global,
    max_active_runs_per_owner,
    max_history_chars,
    max_message_chars,
    max_model_calls,
    max_output_tokens,
    max_tool_result_chars,
    model_name,
)
from database.db import connect
from database.seed import today
from security.auth import ActorContext, require_owner


class RunLimitError(RuntimeError):
    """A run was rejected by a deterministic admission or size limit."""


@dataclass(frozen=True)
class Price:
    input_per_million_usd: float
    output_per_million_usd: float


PRICES: dict[tuple[str, str], Price] = {
    ("gemini", "gemini-3.1-flash-lite"): Price(0.25, 1.50),
    ("openai", "gpt-4.1-mini"): Price(0.40, 1.60),
}


def provider_and_model() -> tuple[str, str]:
    provider = ai_mode()
    if provider == "gemini":
        return provider, gemini_model_name()
    if provider == "openai":
        return provider, model_name()
    raise RunLimitError("Offline mode does not create paid model runs.")


def validate_message(message: str) -> str:
    cleaned = message.strip()
    if not cleaned:
        raise ValueError("Enter a question.")
    if len(cleaned) > max_message_chars():
        raise RunLimitError(
            f"Message is too long. Use at most {max_message_chars()} characters."
        )
    return cleaned


def bounded_history(history: list | None) -> list:
    if not history:
        return []
    selected: list = []
    used = 0
    for item in reversed(history):
        size = len(json.dumps(item, ensure_ascii=False, default=str))
        if selected and used + size > max_history_chars():
            break
        if size > max_history_chars():
            continue
        selected.append(item)
        used += size
    selected.reverse()
    while selected and isinstance(selected[0], dict) and selected[0].get("role") != "user":
        selected.pop(0)
    return selected


def serialize_tool_result(value: object, evidence: dict) -> str:
    payload = value if isinstance(value, dict) and "evidence" in value else {
        "data": value,
        "evidence": evidence,
    }
    encoded = json.dumps(payload, ensure_ascii=False, default=str)
    if len(encoded) <= max_tool_result_chars():
        return encoded

    pages: list[dict] = []
    if isinstance(payload, dict):
        if isinstance(payload.get("data"), dict) and isinstance(payload["data"].get("items"), list):
            pages.append(payload["data"])
        for candidate in payload.values():
            if isinstance(candidate, dict) and isinstance(candidate.get("items"), list):
                pages.append(candidate)
    while pages and len(encoded) > max_tool_result_chars():
        changed = False
        for page in pages:
            items = page["items"]
            if items:
                page["items"] = items[: max(0, len(items) // 2)]
                page["returned_count"] = len(page["items"])
                page["truncated"] = True
                changed = True
        encoded = json.dumps(payload, ensure_ascii=False, default=str)
        if not changed:
            break
    if len(encoded) > max_tool_result_chars():
        encoded = json.dumps({
            "error": "tool_result_too_large",
            "message": "The result exceeded the configured safe size. Narrow the request.",
            "evidence": evidence,
        }, ensure_ascii=False, default=str)
    return encoded


def reserve_run(actor: ActorContext, db_path: str | Path | None = None) -> str:
    actor = require_owner(actor)
    provider, model = provider_and_model()
    price = PRICES.get((provider, model))
    if price is None:
        raise RunLimitError("No approved price entry exists for the configured provider/model.")

    estimated_input_tokens = 6000 * max_model_calls()
    estimated_output_tokens = max_output_tokens() * max_model_calls()
    estimate = round(
        estimated_input_tokens * price.input_per_million_usd
        + estimated_output_tokens * price.output_per_million_usd
    )
    reserved = max(20_000, round(estimate * 1.5))
    now = today()
    run_id = uuid4().hex
    expires = now + timedelta(minutes=2)

    with connect(db_path) as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("""UPDATE ai_usage SET status = 'unknown', updated_at = ?
            WHERE status = 'active' AND expires_at <= ?""",
                   (now.isoformat(timespec="seconds"), now.isoformat(timespec="seconds")))
        owner_active = db.execute(
            "SELECT COUNT(*) FROM ai_usage WHERE status = 'active' AND actor_id = ?",
            (actor.actor_id,),
        ).fetchone()[0]
        global_active = db.execute(
            "SELECT COUNT(*) FROM ai_usage WHERE status = 'active'"
        ).fetchone()[0]
        if owner_active >= max_active_runs_per_owner():
            raise RunLimitError("Another AI request is already running for this owner.")
        if global_active >= max_active_runs_global():
            raise RunLimitError("The pilot is at its AI concurrency limit. Retry shortly.")

        used = db.execute("""SELECT COALESCE(SUM(CASE
                WHEN status = 'settled' THEN COALESCE(actual_usd_micros, reserved_usd_micros)
                ELSE reserved_usd_micros END), 0)
            FROM ai_usage WHERE usage_date = ? AND status IN ('active', 'settled', 'unknown')""",
            (now.date().isoformat(),)).fetchone()[0]
        if used + reserved > daily_budget_usd_micros():
            raise RunLimitError("The synthetic pilot's daily AI budget is exhausted.")
        db.execute("""INSERT INTO ai_usage
            (run_id, actor_id, provider, model, usage_date, reserved_usd_micros,
             status, created_at, updated_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)""",
            (run_id, actor.actor_id, provider, model, now.date().isoformat(), reserved,
             now.isoformat(timespec="seconds"), now.isoformat(timespec="seconds"),
             expires.isoformat(timespec="seconds")))
    return run_id


def settle_run(run_id: str, input_tokens: int, output_tokens: int,
               model_calls: int, tool_calls: int,
               db_path: str | Path | None = None) -> None:
    with connect(db_path) as db:
        row = db.execute("SELECT provider, model FROM ai_usage WHERE run_id = ?", (run_id,)).fetchone()
        if not row:
            raise RunLimitError("Unknown usage reservation.")
        price = PRICES.get((row["provider"], row["model"]))
        if price is None:
            raise RunLimitError("No approved price entry exists for this run.")
        actual = round(input_tokens * price.input_per_million_usd
                       + output_tokens * price.output_per_million_usd)
        db.execute("""UPDATE ai_usage SET status = 'settled', actual_usd_micros = ?,
            input_tokens = ?, output_tokens = ?, model_calls = ?, tool_calls = ?, updated_at = ?
            WHERE run_id = ? AND status = 'active'""",
            (actual, input_tokens, output_tokens, model_calls, tool_calls,
             today().isoformat(timespec="seconds"), run_id))


def mark_run_unknown(run_id: str, model_calls: int, tool_calls: int,
                     db_path: str | Path | None = None) -> None:
    with connect(db_path) as db:
        db.execute("""UPDATE ai_usage SET status = 'unknown', model_calls = ?, tool_calls = ?,
            updated_at = ? WHERE run_id = ? AND status = 'active'""",
            (model_calls, tool_calls, today().isoformat(timespec="seconds"), run_id))


def release_run(run_id: str, db_path: str | Path | None = None) -> None:
    with connect(db_path) as db:
        db.execute("""UPDATE ai_usage SET status = 'released', updated_at = ?
            WHERE run_id = ? AND status = 'active'""",
            (today().isoformat(timespec="seconds"), run_id))


def daily_usage(db_path: str | Path | None = None) -> dict:
    usage_date = today().date().isoformat()
    with connect(db_path) as db:
        row = db.execute("""SELECT COUNT(*) AS run_count,
            COALESCE(SUM(CASE WHEN status = 'settled'
                THEN COALESCE(actual_usd_micros, reserved_usd_micros)
                WHEN status IN ('active', 'unknown') THEN reserved_usd_micros ELSE 0 END), 0) AS used
            FROM ai_usage WHERE usage_date = ?""", (usage_date,)).fetchone()
    return {
        "usage_date": usage_date,
        "run_count": row["run_count"],
        "used_or_reserved_usd": row["used"] / 1_000_000,
        "daily_budget_usd": daily_budget_usd_micros() / 1_000_000,
    }

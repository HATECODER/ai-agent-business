"""Payload-bound proposals, confirmations, idempotency, and audit events."""

from datetime import timedelta
import hashlib
import json
from pathlib import Path
from uuid import uuid4

from database.db import connect
from database.models import CampaignInput, TaskInput
from database.seed import today
from security.auth import ActorContext, require_owner
from tools.growth import create_campaign_brief
from tools.operations import create_task
from workflows.inventory_workflow import run_low_stock_workflow


ALLOWED_ACTIONS = {"create_task", "create_campaign_draft", "run_restock_review"}


def _canonical(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash(payload_json: str) -> str:
    return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()


def propose_action(action_type: str, payload: dict, actor: ActorContext,
                   db_path: str | Path | None = None,
                   idempotency_key: str | None = None) -> dict:
    actor = require_owner(actor)
    if action_type not in ALLOWED_ACTIONS:
        raise ValueError("Unsupported proposed action.")
    payload = _validated_payload(action_type, payload)
    payload_json = _canonical(payload)
    payload_hash = _hash(payload_json)
    logical_key = idempotency_key or _hash(
        f"{actor.actor_id}|{action_type}|{payload_hash}"
    )
    now = today()
    expires = now + timedelta(hours=1)
    with connect(db_path) as db:
        db.execute("BEGIN IMMEDIATE")
        existing = db.execute(
            "SELECT * FROM action_proposals WHERE idempotency_key = ?", (logical_key,)
        ).fetchone()
        if existing:
            if existing["payload_hash"] != payload_hash or existing["action_type"] != action_type:
                raise ValueError("Idempotency key was already used with a different payload.")
            return {**dict(existing), "created": False, "payload": json.loads(existing["payload_json"])}
        proposal_id = uuid4().hex
        db.execute("""INSERT INTO action_proposals
            (id, actor_id, action_type, payload_json, payload_hash, idempotency_key,
             status, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)""",
            (proposal_id, actor.actor_id, action_type, payload_json, payload_hash,
             logical_key, now.isoformat(timespec="seconds"), expires.isoformat(timespec="seconds")))
        _audit(db, actor.actor_id, "action.proposed", "proposal", proposal_id, "pending")
    return {
        "id": proposal_id, "action_type": action_type, "payload": payload,
        "payload_hash": payload_hash, "status": "pending", "created": True,
        "expires_at": expires.isoformat(timespec="seconds"),
    }


def list_pending_proposals(actor: ActorContext, db_path: str | Path | None = None) -> list[dict]:
    actor = require_owner(actor)
    now = today().isoformat(timespec="seconds")
    with connect(db_path) as db:
        rows = db.execute("""SELECT * FROM action_proposals
            WHERE actor_id = ? AND status = 'pending' AND expires_at > ?
            ORDER BY created_at""", (actor.actor_id, now)).fetchall()
    return [{**dict(row), "payload": json.loads(row["payload_json"])} for row in rows]


def execute_proposal(proposal_id: str, actor: ActorContext,
                     db_path: str | Path | None = None) -> dict:
    actor = require_owner(actor)
    now = today()
    with connect(db_path) as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM action_proposals WHERE id = ?", (proposal_id,)).fetchone()
        if not row or row["actor_id"] != actor.actor_id:
            raise ValueError("Proposal was not found for this owner.")
        if row["status"] == "succeeded":
            return json.loads(row["result_json"])
        if row["status"] == "executing":
            raise ValueError("This action is already executing or requires manual reconciliation.")
        if row["status"] != "pending":
            raise ValueError(f"Proposal cannot execute from status '{row['status']}'.")
        if row["expires_at"] <= now.isoformat(timespec="seconds"):
            db.execute("UPDATE action_proposals SET status = 'expired', decided_at = ? WHERE id = ?",
                       (now.isoformat(timespec="seconds"), proposal_id))
            _audit(db, actor.actor_id, "action.expired", "proposal", proposal_id, "expired")
            raise ValueError("Proposal expired; create and review a new proposal.")
        payload_json = _canonical(json.loads(row["payload_json"]))
        if _hash(payload_json) != row["payload_hash"]:
            raise ValueError("Proposal payload integrity check failed.")
        existing = db.execute(
            "SELECT * FROM action_executions WHERE idempotency_key = ?", (row["idempotency_key"],)
        ).fetchone()
        if existing:
            if existing["payload_hash"] != row["payload_hash"]:
                raise ValueError("Idempotency key payload mismatch.")
            if existing["status"] == "succeeded":
                return json.loads(existing["result_json"])
            raise ValueError("This action is already executing or requires manual reconciliation.")
        db.execute("""INSERT INTO action_executions
            (idempotency_key, proposal_id, payload_hash, status, started_at)
            VALUES (?, ?, ?, 'executing', ?)""",
            (row["idempotency_key"], proposal_id, row["payload_hash"],
             now.isoformat(timespec="seconds")))
        db.execute("UPDATE action_proposals SET status = 'executing', decided_at = ? WHERE id = ?",
                   (now.isoformat(timespec="seconds"), proposal_id))

    payload = json.loads(row["payload_json"])
    try:
        result = _execute(row["action_type"], payload, db_path)
    except Exception:
        with connect(db_path) as db:
            db.execute("UPDATE action_executions SET status = 'failed', completed_at = ? WHERE proposal_id = ?",
                       (today().isoformat(timespec="seconds"), proposal_id))
            db.execute("UPDATE action_proposals SET status = 'failed' WHERE id = ?", (proposal_id,))
            _audit(db, actor.actor_id, "action.executed", "proposal", proposal_id, "failed")
        raise

    result_json = json.dumps(result, ensure_ascii=False, default=str)
    with connect(db_path) as db:
        finished = today().isoformat(timespec="seconds")
        db.execute("""UPDATE action_executions SET status = 'succeeded', completed_at = ?, result_json = ?
            WHERE proposal_id = ?""", (finished, result_json, proposal_id))
        db.execute("""UPDATE action_proposals SET status = 'succeeded', result_json = ?
            WHERE id = ?""", (result_json, proposal_id))
        _audit(db, actor.actor_id, "action.executed", "proposal", proposal_id, "succeeded")
    return result


def reject_proposal(proposal_id: str, actor: ActorContext,
                    db_path: str | Path | None = None) -> None:
    actor = require_owner(actor)
    with connect(db_path) as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT actor_id, status FROM action_proposals WHERE id = ?", (proposal_id,)).fetchone()
        if not row or row["actor_id"] != actor.actor_id or row["status"] != "pending":
            raise ValueError("Pending proposal was not found for this owner.")
        db.execute("UPDATE action_proposals SET status = 'rejected', decided_at = ? WHERE id = ?",
                   (today().isoformat(timespec="seconds"), proposal_id))
        _audit(db, actor.actor_id, "action.rejected", "proposal", proposal_id, "rejected")


def _execute(action_type: str, payload: dict, db_path: str | Path | None) -> dict:
    if action_type == "create_task":
        return create_task(**payload, db_path=db_path)
    if action_type == "create_campaign_draft":
        return create_campaign_brief(**payload, db_path=db_path)
    if action_type == "run_restock_review":
        return run_low_stock_workflow(db_path)
    raise ValueError("Unsupported action.")


def _validated_payload(action_type: str, payload: dict) -> dict:
    if action_type == "create_task":
        return TaskInput.model_validate(payload).model_dump()
    if action_type == "create_campaign_draft":
        return CampaignInput.model_validate(payload).model_dump()
    if action_type == "run_restock_review":
        if payload:
            raise ValueError("Restock-review proposals do not accept arguments.")
        return {}
    raise ValueError("Unsupported action.")


def _audit(db, actor_id: str, event_type: str, target_type: str,
           target_id: str, outcome: str) -> None:
    db.execute("""INSERT INTO audit_events
        (actor_id, event_type, target_type, target_id, outcome, created_at)
        VALUES (?, ?, ?, ?, ?, ?)""",
        (actor_id, event_type, target_type, target_id, outcome,
         today().isoformat(timespec="seconds")))

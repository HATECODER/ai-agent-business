from concurrent.futures import ThreadPoolExecutor
import json

import pytest

import services.actions as actions
from database.db import connect
from security.auth import ActorContext, AuthorizationError, demo_actor
from services.actions import execute_proposal, list_pending_proposals, propose_action, reject_proposal
from tools.operations import get_low_stock_products


def test_proposal_is_payload_bound_and_idempotent(seeded_db):
    actor = demo_actor()
    payload = {"title": "Call supplier", "description": "Review stock",
               "priority": "high", "category": "operations"}
    first = propose_action("create_task", payload, actor, seeded_db,
                           idempotency_key="fixed-task-request")
    second = propose_action("create_task", payload, actor, seeded_db,
                            idempotency_key="fixed-task-request")
    assert first["id"] == second["id"]
    assert first["created"] is True
    assert second["created"] is False

    with pytest.raises(ValueError, match="different payload"):
        propose_action("create_task", {**payload, "title": "Different task"}, actor, seeded_db,
                       idempotency_key="fixed-task-request")


def test_confirmation_executes_exactly_once_and_audits(seeded_db):
    actor = demo_actor()
    proposal = propose_action("create_task", {
        "title": "Review delivery", "description": "Check delay",
        "priority": "medium", "category": "operations",
    }, actor, seeded_db)
    before = _count(seeded_db, "tasks")
    result = execute_proposal(proposal["id"], actor, seeded_db)
    replay = execute_proposal(proposal["id"], actor, seeded_db)
    assert result["id"] == replay["id"]
    assert _count(seeded_db, "tasks") == before + 1
    with connect(seeded_db) as db:
        events = db.execute("SELECT event_type, outcome FROM audit_events ORDER BY id").fetchall()
    assert [(row["event_type"], row["outcome"]) for row in events] == [
        ("action.proposed", "pending"), ("action.executed", "succeeded")]


def test_changed_payload_and_wrong_actor_are_rejected(seeded_db, monkeypatch):
    actor = demo_actor()
    proposal = propose_action("create_task", {
        "title": "Review invoice", "description": "Check source",
        "priority": "medium", "category": "finance",
    }, actor, seeded_db)
    with connect(seeded_db) as db:
        db.execute("UPDATE action_proposals SET payload_json = ? WHERE id = ?",
                   (json.dumps({"title": "Changed"}), proposal["id"]))
    with pytest.raises(ValueError, match="integrity"):
        execute_proposal(proposal["id"], actor, seeded_db)

    monkeypatch.setenv("BIZPILOT_DEPLOYMENT_MODE", "pilot")
    monkeypatch.setenv("BIZPILOT_OWNER_SUBJECTS", "https://id.example|right")
    wrong = ActorContext("https://id.example", "wrong", "Wrong", actor.session_expires_at)
    with pytest.raises(AuthorizationError):
        list_pending_proposals(wrong, seeded_db)


def test_rejected_proposal_cannot_execute(seeded_db):
    actor = demo_actor()
    proposal = propose_action("run_restock_review", {}, actor, seeded_db)
    reject_proposal(proposal["id"], actor, seeded_db)
    with pytest.raises(ValueError, match="rejected"):
        execute_proposal(proposal["id"], actor, seeded_db)


def test_executing_proposal_returns_retryable_concurrency_error(seeded_db):
    actor = demo_actor()
    proposal = propose_action("run_restock_review", {}, actor, seeded_db)
    with connect(seeded_db) as db:
        db.execute(
            "UPDATE action_proposals SET status = 'executing' WHERE id = ?",
            (proposal["id"],),
        )

    with pytest.raises(ValueError, match="already executing"):
        execute_proposal(proposal["id"], actor, seeded_db)


def test_parallel_restock_confirmation_has_one_logical_effect(seeded_db):
    actor = demo_actor()
    proposal = propose_action("run_restock_review", {}, actor, seeded_db)

    def confirm():
        try:
            return execute_proposal(proposal["id"], actor, seeded_db)
        except ValueError as error:
            return str(error)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: confirm(), range(2)))

    assert any(isinstance(result, dict) for result in results)
    with connect(seeded_db) as db:
        count = db.execute("SELECT COUNT(*) FROM tasks WHERE category = 'restock'").fetchone()[0]
        executions = db.execute("SELECT COUNT(*) FROM action_executions").fetchone()[0]
    assert count == len(get_low_stock_products(seeded_db))
    assert executions == 1


def test_execution_failure_is_recorded_without_success_claim(seeded_db, monkeypatch):
    actor = demo_actor()
    proposal = propose_action("create_task", {
        "title": "Review failure", "description": "Synthetic failure",
        "priority": "low", "category": "operations",
    }, actor, seeded_db)
    monkeypatch.setattr(actions, "_execute", lambda *args: (_ for _ in ()).throw(
        RuntimeError("synthetic database failure")))
    with pytest.raises(RuntimeError, match="synthetic"):
        execute_proposal(proposal["id"], actor, seeded_db)
    with connect(seeded_db) as db:
        proposal_status = db.execute(
            "SELECT status FROM action_proposals WHERE id = ?", (proposal["id"],)
        ).fetchone()[0]
        execution_status = db.execute(
            "SELECT status FROM action_executions WHERE proposal_id = ?", (proposal["id"],)
        ).fetchone()[0]
    assert proposal_status == execution_status == "failed"


def _count(path, table):
    with connect(path) as db:
        return db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

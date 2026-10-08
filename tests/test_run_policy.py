import asyncio
from datetime import timedelta
import json
from types import SimpleNamespace

import pytest

import agent
from agent import ask_copilot, build_copilot
from database.db import connect
from database.seed import today
from security.auth import ActorContext, demo_actor
from services.run_policy import (
    RunLimitError,
    bounded_history,
    daily_usage,
    mark_run_unknown,
    release_run,
    reserve_run,
    serialize_tool_result,
    settle_run,
    validate_message,
)


def test_message_history_and_tool_result_limits(monkeypatch):
    monkeypatch.setenv("BIZPILOT_MAX_MESSAGE_CHARS", "100")
    with pytest.raises(RunLimitError, match="too long"):
        validate_message("x" * 101)

    monkeypatch.setenv("BIZPILOT_MAX_HISTORY_CHARS", "1000")
    history = [{"role": "user", "content": "x" * 700},
               {"role": "assistant", "content": "y" * 700},
               {"role": "user", "content": "recent"}]
    assert bounded_history(history) == [{"role": "user", "content": "recent"}]

    monkeypatch.setenv("BIZPILOT_MAX_TOOL_RESULT_CHARS", "1000")
    page = {"items": [{"value": "z" * 300} for _ in range(20)],
            "total_count": 20, "returned_count": 20, "truncated": False}
    encoded = serialize_tool_result(page, {"source": "test"})
    assert len(encoded) <= 1000
    assert json.loads(encoded)["data"]["truncated"] is True


def test_atomic_concurrency_and_daily_budget(monkeypatch, seeded_db):
    actor = demo_actor()
    first = reserve_run(actor, seeded_db)
    with pytest.raises(RunLimitError, match="already running"):
        reserve_run(actor, seeded_db)

    second_actor = ActorContext("local-demo", "second", "Second", actor.session_expires_at)
    second = reserve_run(second_actor, seeded_db)
    third_actor = ActorContext("local-demo", "third", "Third", actor.session_expires_at)
    with pytest.raises(RunLimitError, match="concurrency"):
        reserve_run(third_actor, seeded_db)
    release_run(first, seeded_db)
    release_run(second, seeded_db)

    monkeypatch.setenv("BIZPILOT_DAILY_BUDGET_USD", "0.01")
    with pytest.raises(RunLimitError, match="budget"):
        reserve_run(actor, seeded_db)


def test_usage_settlement_unknown_and_restart_visibility(seeded_db):
    actor = demo_actor()
    run_id = reserve_run(actor, seeded_db)
    settle_run(run_id, 1000, 100, 2, 1, seeded_db)
    visible = daily_usage(seeded_db)
    assert visible["run_count"] == 1
    assert visible["used_or_reserved_usd"] > 0
    with connect(seeded_db) as db:
        row = db.execute("SELECT status, input_tokens, tool_calls FROM ai_usage WHERE run_id = ?",
                         (run_id,)).fetchone()
    assert tuple(row) == ("settled", 1000, 1)

    unknown_id = reserve_run(actor, seeded_db)
    mark_run_unknown(unknown_id, 1, 0, seeded_db)
    with connect(seeded_db) as db:
        assert db.execute("SELECT status FROM ai_usage WHERE run_id = ?",
                          (unknown_id,)).fetchone()[0] == "unknown"


def test_runner_uses_limits_and_records_usage(monkeypatch, seeded_db):
    monkeypatch.setenv("BIZPILOT_AI_MODE", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-never-sent")
    captured = {}

    class FakeResult:
        final_output = "verified response"
        context_wrapper = SimpleNamespace(usage=SimpleNamespace(input_tokens=100, output_tokens=20))

        def to_input_list(self):
            return [{"role": "user", "content": "stock"},
                    {"role": "assistant", "content": self.final_output}]

    async def fake_run(*args, **kwargs):
        captured.update(kwargs)
        hooks = kwargs["hooks"]
        await hooks.on_llm_start(None, None, None, [])
        await hooks.on_llm_end(None, None, None)
        return FakeResult()

    monkeypatch.setattr(agent.Runner, "run", fake_run)
    events = []
    answer, _ = ask_copilot("show stock", db_path=seeded_db, event_sink=events)
    assert answer == "verified response"
    assert captured["max_turns"] == 4
    assert captured["run_config"].tracing_disabled is True
    assert captured["run_config"].trace_include_sensitive_data is False
    assert any(event["type"] == "usage" for event in events)
    with connect(seeded_db) as db:
        assert db.execute("SELECT status FROM ai_usage").fetchone()[0] == "settled"


def test_runner_timeout_is_retained_as_unknown(monkeypatch, seeded_db):
    monkeypatch.setenv("BIZPILOT_AI_MODE", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-never-sent")
    monkeypatch.setattr(agent, "run_deadline_seconds", lambda: 0.01)

    async def slow_run(*args, **kwargs):
        await asyncio.sleep(0.05)

    monkeypatch.setattr(agent.Runner, "run", slow_run)
    with pytest.raises(RuntimeError, match="deadline"):
        ask_copilot("show stock", db_path=seeded_db)
    with connect(seeded_db) as db:
        assert db.execute("SELECT status FROM ai_usage").fetchone()[0] == "unknown"


def test_authentication_failure_releases_reservation_without_fallback(monkeypatch, seeded_db):
    monkeypatch.setenv("BIZPILOT_AI_MODE", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-never-sent")

    class FakeAuthenticationError(Exception):
        pass

    async def rejected(*args, **kwargs):
        raise FakeAuthenticationError("synthetic rejected key")

    monkeypatch.setattr(agent, "AuthenticationError", FakeAuthenticationError)
    monkeypatch.setattr(agent.Runner, "run", rejected)
    with pytest.raises(RuntimeError, match="rejected"):
        ask_copilot("show stock", db_path=seeded_db)
    with connect(seeded_db) as db:
        assert db.execute("SELECT status FROM ai_usage").fetchone()[0] == "released"


def test_today_finance_is_backend_dated_without_model(monkeypatch, seeded_db):
    monkeypatch.setenv("BIZPILOT_AI_MODE", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-never-sent")
    monkeypatch.setattr(agent.Runner, "run", lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("today finance must not call model")))
    answer, _ = ask_copilot("ajker financial summary dao", db_path=seeded_db)
    assert today().date().isoformat() in answer
    assert "cash flow is unavailable" in answer.casefold()
    assert "2025" not in answer


def test_tool_rechecks_actor_after_revocation(monkeypatch, seeded_db):
    issuer, subject = "https://id.example", "owner"
    monkeypatch.setenv("BIZPILOT_DEPLOYMENT_MODE", "pilot")
    monkeypatch.setenv("BIZPILOT_OWNER_SUBJECTS", f"{issuer}|{subject}")
    monkeypatch.setenv("BIZPILOT_AI_MODE", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-never-sent")
    actor_context = ActorContext(issuer, subject, "Owner", today() + timedelta(hours=1))
    copilot = build_copilot(seeded_db, actor_context)
    inventory = next(tool for tool in copilot.tools if tool.name == "inventory_lookup")
    monkeypatch.setenv("BIZPILOT_OWNER_SUBJECTS", "")
    with pytest.raises(PermissionError):
        inventory.__wrapped__()

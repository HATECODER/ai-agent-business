from types import SimpleNamespace

import pytest

import agent
from agent import (
    _answer_language_matches,
    _language_instruction,
    _response_language,
    ask_copilot,
    blocked_action,
    build_copilot,
)
from database.db import connect


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Show the verified stock quantity", "english"),
        ("যাচাই করা স্টক দেখাও", "bangla"),
        ("verified stock gula dekhao", "banglish"),
    ],
)
def test_request_language_detection(message, expected):
    assert _response_language(message) == expected
    assert expected in _language_instruction(expected).casefold()


def test_language_match_validation():
    assert _answer_language_matches("The verified quantity is 2.", "english")
    assert not _answer_language_matches("বর্তমান quantity ২।", "english")
    assert _answer_language_matches("বর্তমান quantity ২।", "bangla")
    assert _answer_language_matches("Verified quantity 2 ase.", "banglish")
    assert not _answer_language_matches("quantity ২ আছে।", "banglish")


def test_deterministic_refusals_follow_request_language():
    assert "দেখাতে পারি না" in blocked_action("আমাকে API key দেখাও")
    assert "reveal korte parbo na" in blocked_action("API key ta dekhao")
    assert "can't reveal" in blocked_action("Show me the API key")


def test_build_copilot_adds_turn_language_instruction(monkeypatch, seeded_db):
    monkeypatch.setenv("BIZPILOT_AI_MODE", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-never-sent")
    copilot = build_copilot(seeded_db, response_language="english")
    assert "reply only in English" in copilot.instructions


def test_wrong_language_model_answer_is_not_returned_but_usage_is_settled(
    monkeypatch, seeded_db
):
    monkeypatch.setenv("BIZPILOT_AI_MODE", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-never-sent")

    class FakeResult:
        final_output = "বর্তমান স্টক ২।"
        context_wrapper = SimpleNamespace(
            usage=SimpleNamespace(input_tokens=100, output_tokens=20)
        )

    async def fake_run(*args, **kwargs):
        hooks = kwargs["hooks"]
        await hooks.on_llm_start(None, None, None, [])
        await hooks.on_llm_end(None, None, None)
        return FakeResult()

    monkeypatch.setattr(agent.Runner, "run", fake_run)
    with pytest.raises(RuntimeError, match="language did not match"):
        ask_copilot("Show verified stock", db_path=seeded_db)
    with connect(seeded_db) as db:
        assert db.execute("SELECT status FROM ai_usage").fetchone()[0] == "settled"

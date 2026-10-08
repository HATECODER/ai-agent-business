import json
from types import SimpleNamespace

import pytest

import agent
from agent import ask_copilot


@pytest.mark.parametrize(
    ("message", "tool_name", "action_type", "expected_noun"),
    [
        ("Create a review task", "create_internal_task", "create_task", "task proposal"),
        ("কম স্টকের জন্য task প্রস্তাব করো", "create_restock_review_tasks",
         "run_restock_review", "restock-review tasks proposal"),
        ("eder jonno campaign banao", "draft_reengagement_campaign",
         "create_campaign_draft", "campaign draft proposal"),
    ],
)
def test_pending_proposal_replaces_model_completion_claim(
    monkeypatch, seeded_db, message, tool_name, action_type, expected_noun
):
    monkeypatch.setenv("BIZPILOT_AI_MODE", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-never-sent")

    class FakeResult:
        final_output = "The action was created and completed."
        context_wrapper = SimpleNamespace(
            usage=SimpleNamespace(input_tokens=100, output_tokens=20)
        )

    async def fake_run(*args, **kwargs):
        hooks = kwargs["hooks"]
        tool = SimpleNamespace(name=tool_name)
        context = SimpleNamespace(tool_arguments="{}")
        await hooks.on_llm_start(None, None, None, [])
        await hooks.on_tool_start(context, None, tool)
        result = json.dumps({
            "data": {"status": "pending", "action_type": action_type},
            "evidence": {"source": "test"},
        })
        await hooks.on_tool_end(context, None, tool, result)
        await hooks.on_llm_end(None, None, None)
        return FakeResult()

    monkeypatch.setattr(agent.Runner, "run", fake_run)
    answer, _ = ask_copilot(message, db_path=seeded_db)

    assert expected_noun in answer
    assert "Proposal status:" in answer
    assert "pending" in answer
    assert "confirm" in answer
    assert "The action was created and completed." not in answer

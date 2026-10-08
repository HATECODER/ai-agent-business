import pytest

from agent import ask_copilot
from security.auth import demo_actor


@pytest.mark.parametrize(
    ("question", "snapshot_text"),
    [
        ("Which source and timestamp support those results?", "synthetic snapshot"),
        ("এগুলোর তথ্য কখন query করা হয়েছে?", "synthetic snapshot"),
        ("egular source ar query time bolo", "synthetic snapshot"),
    ],
)
def test_evidence_followup_uses_previous_structured_metadata(
    monkeypatch, seeded_db, question, snapshot_text
):
    monkeypatch.setenv("BIZPILOT_AI_MODE", "offline")
    monkeypatch.setenv("BIZPILOT_DATA_MODE", "synthetic")
    answer, history = ask_copilot(
        "kon product stock kom?", [], seeded_db, actor=demo_actor()
    )
    assert "<bizpilot_evidence>" not in answer
    stored_timestamp = history[-1]["content"].split('"queried_at":"', 1)[1].split('"', 1)[0]

    followup, next_history = ask_copilot(
        question, history, seeded_db, actor=demo_actor()
    )

    assert "Source:" in followup
    assert "Queried at:" in followup
    assert stored_timestamp in followup
    assert snapshot_text in followup
    assert "real-time data" in followup
    assert "<bizpilot_evidence>" not in followup
    assert len(next_history) > len(history)

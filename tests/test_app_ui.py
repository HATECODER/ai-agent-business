from database.db import connect
from pathlib import Path
from streamlit.testing.v1 import AppTest


APP = Path(__file__).resolve().parents[1] / "app.py"


def configure_demo(monkeypatch, tmp_path):
    database = tmp_path / "ui.sqlite3"
    monkeypatch.setenv("BIZPILOT_DEPLOYMENT_MODE", "demo")
    monkeypatch.setenv("BIZPILOT_DATA_MODE", "synthetic")
    monkeypatch.setenv("BIZPILOT_AI_MODE", "offline")
    monkeypatch.setenv("BIZPILOT_DB_PATH", str(database))
    return database


def test_dashboard_shows_evidence_and_truthful_finance_labels(monkeypatch, tmp_path):
    configure_demo(monkeypatch, tmp_path)
    app = AppTest.from_file(APP, default_timeout=10).run()
    assert not app.exception
    assert [title.value for title in app.title] == ["BizPilot AI"]
    captions = " ".join(item.value for item in app.caption)
    assert "fictional-v1" in captions
    assert "Bangladesh date" in captions
    labels = {metric.label for metric in app.metric}
    assert "Receipts on today's orders" in labels
    assert "Receivable on today's orders" in labels
    assert "Net cash flow" not in labels
    warnings = " ".join(item.value for item in app.warning)
    assert "not cash flow" in warnings


def test_ui_write_requires_confirmation_and_replay_is_safe(monkeypatch, tmp_path):
    database = configure_demo(monkeypatch, tmp_path)
    app = AppTest.from_file(APP, default_timeout=10).run()
    propose = next(button for button in app.button
                   if button.label == "Propose low-stock review tasks")
    propose.click().run()
    with connect(database) as db:
        assert db.execute("SELECT COUNT(*) FROM tasks WHERE category = 'restock'").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM action_proposals").fetchone()[0] == 1

    # Repeating the same logical proposal returns the existing pending record.
    propose = next(button for button in app.button
                   if button.label == "Propose low-stock review tasks")
    propose.click().run()
    with connect(database) as db:
        assert db.execute("SELECT COUNT(*) FROM action_proposals").fetchone()[0] == 1

    confirm = next(button for button in app.button if button.label == "Confirm exact action")
    confirm.click().run()
    with connect(database) as db:
        restock_count = db.execute(
            "SELECT COUNT(*) FROM tasks WHERE category = 'restock'"
        ).fetchone()[0]
        low_stock_count = db.execute(
            "SELECT COUNT(*) FROM inventory WHERE quantity <= low_stock_threshold"
        ).fetchone()[0]
        assert restock_count == low_stock_count
        assert db.execute("SELECT COUNT(*) FROM action_executions").fetchone()[0] == 1


def test_invalid_configuration_stops_before_dashboard(monkeypatch, tmp_path):
    configure_demo(monkeypatch, tmp_path)
    monkeypatch.setenv("BIZPILOT_DATA_MODE", "real-unreviewed")
    app = AppTest.from_file(APP, default_timeout=10).run()
    assert not app.exception
    assert any("BIZPILOT_DATA_MODE" in error.value for error in app.error)

import pytest

from database.db import connect, prepare_database
from services.data_evidence import bounded_rows, data_evidence


def test_demo_may_seed_fictional_data(monkeypatch, tmp_path):
    monkeypatch.setenv("BIZPILOT_DEPLOYMENT_MODE", "demo")
    monkeypatch.setenv("BIZPILOT_DATA_MODE", "synthetic")
    path = tmp_path / "demo.sqlite3"
    prepare_database(path)
    with connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 24


def test_pilot_missing_database_fails_without_creating_file(monkeypatch, tmp_path):
    monkeypatch.setenv("BIZPILOT_DEPLOYMENT_MODE", "pilot")
    monkeypatch.setenv("BIZPILOT_DATA_MODE", "synthetic")
    path = tmp_path / "missing.sqlite3"
    with pytest.raises(RuntimeError, match="missing"):
        prepare_database(path)
    assert not path.exists()


def test_pilot_rejects_external_data_mode(monkeypatch, seeded_db):
    monkeypatch.setenv("BIZPILOT_DEPLOYMENT_MODE", "pilot")
    monkeypatch.setenv("BIZPILOT_DATA_MODE", "external")
    with pytest.raises(ValueError, match="synthetic"):
        prepare_database(seeded_db)


def test_bounded_rows_and_evidence(monkeypatch, seeded_db):
    monkeypatch.setenv("BIZPILOT_MAX_RESULT_ROWS", "2")
    page = bounded_rows([{"id": value} for value in range(5)])
    assert page == {
        "items": [{"id": 0}, {"id": 1}],
        "total_count": 5,
        "returned_count": 2,
        "truncated": True,
    }
    evidence = data_evidence(seeded_db)
    assert evidence["dataset_version"] == "fictional-v1"
    assert evidence["freshness"] == "fictional_snapshot"

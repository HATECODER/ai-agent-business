import json
from hashlib import sha256
from pathlib import Path

from backend.app.inventory_import import validate_inventory_csv
from scripts.validate_november_demo_fixtures import (
    calculate_results,
    validate_fixture_pack,
)

FIXTURE_DIR = Path("demo_fixtures/november_v1")


def test_november_fixture_pack_matches_reviewed_results():
    assert validate_fixture_pack(FIXTURE_DIR) == []


def test_november_fixture_contains_required_demo_cases():
    results = calculate_results(FIXTURE_DIR)
    assert results["inventory"]["low_stock_including_out_of_stock"] > 0
    assert results["inventory"]["out_of_stock"] > 0
    assert results["finance_on_reference_date"]["order_cohort_receivable_bdt"] > 0
    assert results["customers"]["inactive_count"] > 0
    assert results["tasks"]["attention_count"] > 0
    assert results["preview_cases"] == {
        "preview-valid.csv": {"new": 1, "changed": 1, "errors": 0, "conflicts": 0},
        "preview-conflict.csv": {"new": 0, "changed": 0, "errors": 0, "conflicts": 1},
        "preview-invalid.csv": {"new": 1, "changed": 0, "errors": 2, "conflicts": 0},
    }


def test_preview_classification_does_not_change_inventory_fixture():
    inventory_path = FIXTURE_DIR / "inventory.csv"
    digest_before = sha256(inventory_path.read_bytes()).hexdigest()

    calculate_results(FIXTURE_DIR)

    assert sha256(inventory_path.read_bytes()).hexdigest() == digest_before


def test_invalid_preview_errors_do_not_echo_formula_payload():
    content = (FIXTURE_DIR / "preview-invalid.csv").read_bytes()
    _, parsed = validate_inventory_csv("preview-invalid.csv", "text/csv", content)
    serialized_errors = json.dumps(
        [error.model_dump() for error in parsed.errors], sort_keys=True
    )

    assert len(parsed.errors) == 2
    assert "=FORMULA" not in serialized_errors

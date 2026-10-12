from scripts.evaluate_november_copilot_languages import evaluate_cases


def test_fifteen_frozen_language_cases_route_to_the_expected_tools():
    result = evaluate_cases()
    assert result["total"] == 15
    assert result["passed"] == 15
    assert result["failed"] == 0
    assert result["language_counts"] == {"Bangla": 5, "Banglish": 5, "English": 5}
    assert result["question_counts"] == {
        "finance": 3,
        "inactive_customers": 3,
        "restock": 3,
        "restock_proposal": 3,
        "tasks": 3,
    }

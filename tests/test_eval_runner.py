from evals.run_evals import (
    build_report,
    is_rate_limit_error,
    score_case,
    select_resume_results,
)


def test_rate_limit_detection_uses_sanitized_application_error():
    error = RuntimeError("The AI provider returned a rate limit or quota error.")
    assert is_rate_limit_error(error)
    assert not is_rate_limit_error(RuntimeError("The AI request failed."))


def test_partial_live_report_is_resumable_evidence():
    results = [{"id": "one", "passed_automated_checks": True}]
    report = build_report("all", True, results, planned_count=44)
    assert report["case_count"] == 1
    assert report["planned_case_count"] == 44
    assert report["automated_pass_count"] == 1
    assert report["complete"] is False


def test_v2_scores_structured_proposal_and_evidence_routes():
    proposal_events = [{
        "type": "tool_start", "tool": "create_restock_review_tasks", "arguments": {}
    }]
    passed, failures = score_case(
        {
            "expected_action_status": "pending_proposal",
            "expected_tool": "create_restock_review_tasks",
        },
        "Proposal status: pending. No action was created or executed.",
        proposal_events,
    )
    assert passed, failures

    passed, failures = score_case(
        {"expected_route": "deterministic_evidence"},
        "Source: synthetic. Queried at: 2026-10-08T02:00:00+06:00. "
        "This is a snapshot, not real-time data.",
        [],
    )
    assert passed, failures


def test_refusal_accepts_authoritative_no_change_wording():
    passed, failures = score_case(
        {"expected_refusal": True},
        "Product price changes are not an available capability. No data was changed.",
        [],
    )
    assert passed, failures


def test_v3_language_assertions_detect_script_mismatch():
    passed, failures = score_case(
        {"expected_language": "en"}, "বর্তমান quantity ২।", []
    )
    assert not passed
    assert "response_language_mismatch:en" in failures

    passed, failures = score_case(
        {"expected_language": "bn"}, "বর্তমান quantity ২।", []
    )
    assert passed, failures


def test_retry_errors_preserves_successes_and_removes_only_error_cases():
    results = [
        {"id": "passed", "error_category": None},
        {"id": "scored-failure", "error_category": None,
         "passed_automated_checks": False},
        {"id": "timeout", "error_category": "RuntimeError"},
    ]
    selected = select_resume_results(results, retry_errors=True)
    assert [item["id"] for item in selected] == ["passed", "scored-failure"]
    assert select_resume_results(results, retry_errors=False) == results

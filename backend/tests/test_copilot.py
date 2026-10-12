from datetime import date, datetime, timezone
from uuid import UUID

import pytest

from backend.app.authorization import AuthorizationDenied, MerchantRole, TenantAuthority
from backend.app.business_facts import (
    AttentionTask,
    AttentionTaskSummary,
    FinanceSummary,
    InactiveCustomerSummary,
)
from backend.app.copilot import CopilotQuestion, build_copilot_reader, classify_question
from backend.app.inventory import InventoryItem, InventoryPage

TENANT_ID = "10000000-0000-0000-0000-000000000001"
REFERENCE_DATE = date(2026, 11, 1)


def authority(role=MerchantRole.OWNER):
    return TenantAuthority(
        identity_id="10000000-0000-0000-0000-000000000002",
        membership_id="10000000-0000-0000-0000-000000000003",
        tenant_id=TENANT_ID,
        role=role,
        permission_version=1,
    )


def inventory_item():
    identifier = UUID("10000000-0000-0000-0000-000000000010")
    return InventoryItem(
        inventory_id=identifier,
        product_id=identifier,
        variant_id=identifier,
        location_id=identifier,
        product_name="Everyday Kurti",
        variant_name="Blue M",
        sku="BP-KUR-BLU-M",
        location_code="DHK",
        location_name="Dhaka Main",
        quantity=0,
        low_stock_threshold=4,
        is_low_stock=True,
        base_price_minor=120000,
        currency="BDT",
        record_version=1,
        source_kind="demo_fixture",
        source_version="november_v1",
        observed_at=datetime(2026, 11, 1, tzinfo=timezone.utc),
    )


def reader():
    return build_copilot_reader(
        lambda *_args: InventoryPage(items=[inventory_item()], limit=100),
        lambda *_args: FinanceSummary(
            reference_date=REFERENCE_DATE,
            order_count=2,
            revenue_bdt=5000,
            receipts_bdt=3500,
            receivable_bdt=1500,
            average_order_value_bdt=2500,
            expenses_bdt=800,
            receipts_less_expenses_bdt=2700,
        ),
        lambda *_args: InactiveCustomerSummary(
            reference_date=REFERENCE_DATE,
            inactive_days=30,
            inactive_customer_keys=["CUST-002", "CUST-004", "CUST-005"],
        ),
        lambda *_args: AttentionTaskSummary(
            tasks=[
                AttentionTask(
                    task_key="TASK-001",
                    title="Confirm dispatch list",
                    category="operations",
                    priority="high",
                    status="pending",
                )
            ]
        ),
    )


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Which products need restocking?", CopilotQuestion.RESTOCK),
        ("আজকের আর্থিক summary", CopilotQuestion.FINANCE),
        ("inactive customer কারা?", CopilotQuestion.INACTIVE_CUSTOMERS),
        ("কোন task attention দরকার?", CopilotQuestion.TASKS),
    ],
)
def test_supported_languages_are_classified(message, expected):
    assert classify_question(message) is expected


def test_answers_use_deterministic_source_facts():
    copilot = reader()
    finance = copilot(authority(), "financial summary", REFERENCE_DATE)
    assert "BDT 5,000 revenue" in finance.answer
    assert finance.mode == "deterministic"
    assert finance.reference_date == REFERENCE_DATE
    assert "complete accounting" in finance.limitations[0]
    assert finance.language == "English"

    restock = copilot(authority(), "restock", REFERENCE_DATE)
    assert "BP-KUR-BLU-M (0 in stock)" in restock.answer
    assert "no purchase or inventory change" in restock.limitations[0]

    proposal = copilot(authority(), "prepare restock proposal", REFERENCE_DATE)
    assert proposal.question_type is CopilotQuestion.RESTOCK_PROPOSAL
    assert proposal.proposal_items[0].suggested_quantity == 8
    assert proposal.proposal_items[0].current_quantity == 0
    assert proposal.sources[1].value == "Review only"
    assert "Nothing was ordered" in proposal.limitations[0]


def test_restock_proposal_prompt_is_classified_before_general_stock_question():
    assert (
        classify_question("Prepare a restock review proposal")
        is CopilotQuestion.RESTOCK_PROPOSAL
    )
    assert (
        classify_question("একটা স্টক প্ল্যান তৈরি করো") is CopilotQuestion.RESTOCK_PROPOSAL
    )


def test_answers_follow_bangla_and_banglish_prompt_language():
    bangla = reader()(authority(), "আজকের আর্থিক সারাংশ দেখাও", REFERENCE_DATE)
    assert bangla.language == "Bangla"
    assert "তারিখে" in bangla.answer
    assert "BDT 5,000" in bangla.answer

    banglish = reader()(authority(), "Ajker financial summary dekhao", REFERENCE_DATE)
    assert banglish.language == "Banglish"
    assert "qualifying order" in banglish.answer
    assert "BDT 5,000" in banglish.answer


def test_deterministic_mode_does_not_require_model_credentials(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    answer = reader()(authority(), "financial summary", REFERENCE_DATE)
    assert answer.mode == "deterministic"
    assert "BDT 5,000 revenue" in answer.answer


def test_missing_source_rows_are_reported_without_invention():
    copilot = build_copilot_reader(
        lambda *_args: InventoryPage(items=[], limit=100),
        lambda *_args: FinanceSummary(
            reference_date=REFERENCE_DATE,
            order_count=0,
            revenue_bdt=0,
            receipts_bdt=0,
            receivable_bdt=0,
            average_order_value_bdt=0,
            expenses_bdt=0,
            receipts_less_expenses_bdt=0,
        ),
        lambda *_args: InactiveCustomerSummary(
            reference_date=REFERENCE_DATE, inactive_days=30, inactive_customer_keys=[]
        ),
        lambda *_args: AttentionTaskSummary(tasks=[]),
    )
    assert copilot(authority(), "restock", REFERENCE_DATE).answer.startswith(
        "No products"
    )
    assert copilot(authority(), "finance", REFERENCE_DATE).answer.startswith(
        "No confirmed"
    )
    assert copilot(authority(), "inactive customers", REFERENCE_DATE).answer.startswith(
        "No customers"
    )
    assert copilot(authority(), "tasks", REFERENCE_DATE).answer.startswith("No pending")


def test_unsupported_question_and_domain_denial_are_preserved():
    with pytest.raises(ValueError):
        reader()(authority(), "write an unrelated poem", REFERENCE_DATE)

    def deny_finance(*_args):
        raise AuthorizationDenied("denied by finance reader")

    domain_restricted = build_copilot_reader(
        lambda *_args: InventoryPage(items=[], limit=100),
        deny_finance,
        lambda *_args: InactiveCustomerSummary(
            reference_date=REFERENCE_DATE, inactive_days=30, inactive_customer_keys=[]
        ),
        lambda *_args: AttentionTaskSummary(tasks=[]),
    )
    with pytest.raises(AuthorizationDenied):
        domain_restricted(
            authority(MerchantRole.OPERATIONS), "financial summary", REFERENCE_DATE
        )

"""Bounded, tenant-scoped Copilot answers for the November demonstration."""

import re
from collections.abc import Callable
from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field

from backend.app.authorization import Permission, TenantAuthority, require_permission
from backend.app.business_facts import FinanceReader, InactiveCustomerReader, TaskReader
from backend.app.inventory import InventoryReader


class CopilotQuestion(StrEnum):
    RESTOCK = "restock"
    RESTOCK_PROPOSAL = "restock_proposal"
    FINANCE = "finance"
    INACTIVE_CUSTOMERS = "inactive_customers"
    TASKS = "tasks"


class SourceFact(BaseModel):
    label: str
    value: str


class RestockProposalItem(BaseModel):
    sku: str
    product: str
    variant: str
    location: str
    current_quantity: int = Field(ge=0)
    low_stock_threshold: int = Field(ge=0)
    suggested_quantity: int = Field(ge=0)
    source: str
    observed_at: str


class CopilotAnswer(BaseModel):
    question_type: CopilotQuestion
    answer: str
    sources: list[SourceFact]
    reference_date: date
    language: str
    mode: str = "deterministic"
    limitations: list[str] = Field(default_factory=list)
    proposal_items: list[RestockProposalItem] = Field(default_factory=list)


CopilotReader = Callable[[TenantAuthority, str, date], CopilotAnswer]


class UnsupportedQuestion(ValueError):
    """The request is outside the deliberately small demo question set."""


def detect_language(message: str) -> str:
    if re.search(r"[\u0980-\u09ff]", message):
        return "Bangla"
    normalized = re.sub(r"[^a-z]+", " ", message.casefold())
    banglish = {
        "ajker",
        "banao",
        "dekhao",
        "din",
        "dorkar",
        "ekta",
        "hobe",
        "kon",
        "korte",
        "kara",
    }
    return "Banglish" if banglish.intersection(normalized.split()) else "English"


def localized(language: str, english: str, bangla: str, banglish: str) -> str:
    return {"English": english, "Bangla": bangla, "Banglish": banglish}[language]


def classify_question(message: str) -> CopilotQuestion:
    normalized = re.sub(r"\s+", " ", message.casefold()).strip()
    if any(
        word in normalized for word in ("proposal", "plan", "প্রস্তাব", "প্ল্যান")
    ) and any(
        word in normalized
        for word in ("restock", "stock", "inventory", "স্টক", "ইনভেন্টরি")
    ):
        return CopilotQuestion.RESTOCK_PROPOSAL
    patterns = (
        (
            CopilotQuestion.FINANCE,
            ("finance", "financial", "revenue", "sales", "টাকা", "বিক্রি", "আর্থিক"),
        ),
        (CopilotQuestion.INACTIVE_CUSTOMERS, ("inactive", "customer", "গ্রাহক", "কাস্টমার")),
        (CopilotQuestion.TASKS, ("task", "attention", "কাজ", "টাস্ক")),
        (
            CopilotQuestion.RESTOCK,
            ("restock", "stock", "inventory", "sku", "স্টক", "ইনভেন্টরি"),
        ),
    )
    for question_type, words in patterns:
        if any(word in normalized for word in words):
            return question_type
    raise UnsupportedQuestion(
        "Ask about restocking, finance, inactive customers, or tasks."
    )


def build_copilot_reader(
    inventory_reader: InventoryReader,
    finance_reader: FinanceReader,
    inactive_customer_reader: InactiveCustomerReader,
    task_reader: TaskReader,
) -> CopilotReader:
    def answer(
        authority: TenantAuthority, message: str, reference_date: date
    ) -> CopilotAnswer:
        require_permission(authority, Permission.COPILOT_USE)
        question_type = classify_question(message)
        language = detect_language(message)

        if question_type in (CopilotQuestion.RESTOCK, CopilotQuestion.RESTOCK_PROPOSAL):
            items = sorted(
                inventory_reader(authority, 100, None, True).items,
                key=lambda item: (item.quantity, item.sku),
            )
            if not items:
                text = localized(
                    language,
                    "No products currently meet the approved low-stock rule.",
                    "অনুমোদিত লো-স্টক নিয়ম অনুযায়ী এখন কোনো পণ্যে ব্যবস্থা প্রয়োজন নেই।",
                    "Approved low-stock rule অনুযায়ী ekhon kono product-e action dorkar nei.",
                )
                return CopilotAnswer(
                    question_type=question_type,
                    answer=text,
                    sources=[
                        SourceFact(label="Inventory rows needing attention", value="0")
                    ],
                    reference_date=reference_date,
                    language=language,
                )
            if question_type is CopilotQuestion.RESTOCK_PROPOSAL:
                proposals = [
                    RestockProposalItem(
                        sku=item.sku,
                        product=item.product_name,
                        variant=item.variant_name,
                        location=item.location_name,
                        current_quantity=item.quantity,
                        low_stock_threshold=item.low_stock_threshold,
                        suggested_quantity=max(
                            0, (2 * item.low_stock_threshold) - item.quantity
                        ),
                        source=item.source_kind,
                        observed_at=item.observed_at.isoformat(),
                    )
                    for item in items
                ]
                total_units = sum(item.suggested_quantity for item in proposals)
                text = localized(
                    language,
                    f"Review {len(proposals)} proposed restock lines totaling {total_units} units.",
                    f"মোট {total_units} ইউনিটের {len(proposals)}টি প্রস্তাবিত রিস্টক লাইন পর্যালোচনা করুন।",
                    f"Mot {total_units} unit-er {len(proposals)}ti proposed restock line review korun.",
                )
                return CopilotAnswer(
                    question_type=question_type,
                    answer=text,
                    sources=[
                        SourceFact(
                            label="Suggestion rule",
                            value="max(0, 2 × low-stock level − current quantity)",
                        ),
                        SourceFact(label="Proposal state", value="Review only"),
                    ],
                    reference_date=reference_date,
                    language=language,
                    limitations=[
                        "Nothing was ordered, purchased, sent, or written to inventory."
                    ],
                    proposal_items=proposals,
                )
            summary = ", ".join(
                f"{item.sku} ({item.quantity} in stock)" for item in items
            )
            text = localized(
                language,
                f"{len(items)} product variants need attention: {summary}.",
                f"{len(items)}টি পণ্য ভ্যারিয়েন্টে ব্যবস্থা প্রয়োজন: {summary}।",
                f"{len(items)}ti product variant-e attention dorkar: {summary}.",
            )
            return CopilotAnswer(
                question_type=question_type,
                answer=text,
                sources=[
                    SourceFact(
                        label="Rule",
                        value="quantity at or below the approved low-stock level",
                    ),
                    SourceFact(label="Matching variants", value=str(len(items))),
                ],
                reference_date=reference_date,
                language=language,
                limitations=[
                    "This is a read-only stock review; no purchase or inventory change was made."
                ],
            )

        if question_type is CopilotQuestion.FINANCE:
            facts = finance_reader(authority, reference_date)
            if facts.order_count == 0:
                text = localized(
                    language,
                    f"No confirmed or delivered sales were found for {reference_date.isoformat()}.",
                    f"{reference_date.isoformat()} তারিখে কোনো confirmed বা delivered sale পাওয়া যায়নি।",
                    f"{reference_date.isoformat()}-e kono confirmed ba delivered sale paoa jayni.",
                )
                return CopilotAnswer(
                    question_type=question_type,
                    answer=text,
                    sources=[SourceFact(label="Qualifying orders", value="0")],
                    reference_date=reference_date,
                    language=language,
                    limitations=[
                        "This summary is not complete accounting, profit, or cash flow."
                    ],
                )
            text = localized(
                language,
                f"For {reference_date.isoformat()}: {facts.order_count} qualifying orders, BDT {facts.revenue_bdt:,} revenue, BDT {facts.receipts_bdt:,} received, BDT {facts.receivable_bdt:,} receivable, and BDT {facts.expenses_bdt:,} expenses.",
                f"{reference_date.isoformat()} তারিখে {facts.order_count}টি qualifying order, revenue BDT {facts.revenue_bdt:,}, receipt BDT {facts.receipts_bdt:,}, receivable BDT {facts.receivable_bdt:,} এবং expense BDT {facts.expenses_bdt:,}।",
                f"{reference_date.isoformat()}-e {facts.order_count}ti qualifying order, revenue BDT {facts.revenue_bdt:,}, receipt BDT {facts.receipts_bdt:,}, receivable BDT {facts.receivable_bdt:,}, ebong expense BDT {facts.expenses_bdt:,}.",
            )
            return CopilotAnswer(
                question_type=question_type,
                answer=text,
                sources=[
                    SourceFact(
                        label="Average order value",
                        value=f"BDT {facts.average_order_value_bdt:,.2f}",
                    ),
                    SourceFact(
                        label="Receipts less expenses",
                        value=f"BDT {facts.receipts_less_expenses_bdt:,}",
                    ),
                ],
                reference_date=reference_date,
                language=language,
                limitations=[
                    "Only confirmed/delivered orders are counted; this is not complete accounting or profit."
                ],
            )

        if question_type is CopilotQuestion.INACTIVE_CUSTOMERS:
            keys = inactive_customer_reader(
                authority, reference_date, 30
            ).inactive_customer_keys
            english = (
                f"{len(keys)} customers were inactive for the approved 30-day window: {', '.join(keys)}."
                if keys
                else "No customers meet the approved 30-day inactivity rule."
            )
            bangla = (
                f"অনুমোদিত ৩০ দিনের হিসাবে {len(keys)} জন গ্রাহক inactive: {', '.join(keys)}।"
                if keys
                else "অনুমোদিত ৩০ দিনের inactivity নিয়মে কোনো গ্রাহক নেই।"
            )
            banglish = (
                f"Approved 30-day window-e {len(keys)} jon customer inactive: {', '.join(keys)}."
                if keys
                else "Approved 30-day inactivity rule-e kono customer nei."
            )
            return CopilotAnswer(
                question_type=question_type,
                answer=localized(language, english, bangla, banglish),
                sources=[
                    SourceFact(label="Inactive window", value="30 days"),
                    SourceFact(label="Customers", value=str(len(keys))),
                ],
                reference_date=reference_date,
                language=language,
                limitations=["Only pseudonymous customer keys are shown."],
            )

        tasks = task_reader(authority).tasks
        task_list = "; ".join(
            f"{task.task_key} — {task.title} [{task.priority}, {task.status}]"
            for task in tasks
        )
        english = (
            f"{len(tasks)} tasks need attention: {task_list}."
            if tasks
            else "No pending or in-progress tasks need attention."
        )
        bangla = (
            f"{len(tasks)}টি কাজে নজর দেওয়া প্রয়োজন: {task_list}।"
            if tasks
            else "নজর দেওয়ার মতো কোনো pending বা in-progress কাজ নেই।"
        )
        banglish = (
            f"{len(tasks)}ti task-e attention dorkar: {task_list}."
            if tasks
            else "Kono pending ba in-progress task-e attention dorkar nei."
        )
        return CopilotAnswer(
            question_type=question_type,
            answer=localized(language, english, bangla, banglish),
            sources=[
                SourceFact(label="Pending or in-progress tasks", value=str(len(tasks)))
            ],
            reference_date=reference_date,
            language=language,
        )

    return answer

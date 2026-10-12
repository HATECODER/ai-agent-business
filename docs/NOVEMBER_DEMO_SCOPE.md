# November Merchant Demo - Scope Freeze

Status: **Day 1 approved by Product Owner on 2026-10-11**
Prepared: 2026-10-11 (Asia/Dhaka)
Plan: [ONE_WEEK_PLAN.md](../ONE_WEEK_PLAN.md)

## Proposed outcome

Deliver one ten-minute, repeatable demonstration for a Bangladeshi retail
merchant using a dedicated staging workspace and synthetic data. The merchant
can sign in, inspect inventory, preview a CSV, ask five supported questions and
review a restock proposal. No external action or inventory update executes.

## Proposed primary walkthrough

1. Sign in with the existing Auth0 staging account.
2. Open the existing `BizPilot Staging Merchant` workspace.
3. Show 10-30 seeded product variants across one or two locations.
4. Search a SKU and filter low-stock/out-of-stock rows.
5. Preview prepared CSV cases: new, changed, invalid and stale conflict.
6. Confirm the preview did not change inventory.
7. Ask the five supported questions in the plan.
8. Review a restock proposal with evidence and suggested quantities.
9. State the prototype limitations and request merchant feedback.

## Frozen technical and business rules

These rules already exist in code or accepted repository documentation:

| Rule | Proposed demo interpretation | Source |
|---|---|---|
| Timezone | `Asia/Dhaka` (UTC+06:00) | Existing database and finance behavior |
| Currency | BDT | Existing database and finance tools |
| Low stock | `quantity <= low_stock_threshold` | Inventory backend and UI |
| Out of stock | `quantity == 0` | Inventory UI |
| Inactive customer | No qualifying recent purchase in the last 30 days | Existing Growth tool default |
| Sales | Confirmed or delivered orders | Existing finance definition |
| Excluded sales | Pending and cancelled orders | Existing finance definition |
| Financial view | Order-cohort operational summary; not cash flow, profit or formal accounting | Existing README boundary |
| CSV action | Preview only; raw data is discarded and inventory is unchanged | Accepted CSV preview decision |
| Restock action | Review-only proposal; no purchase or stock write | November demo boundary |
| AI responsibility | Explain deterministic tool output; never calculate business totals | Repository guidance |

## Five supported questions

1. Which products need restocking?
2. Show today's financial summary.
3. Which customers have been inactive for 30 days?
4. What tasks need attention?
5. Prepare a restock review proposal.

Each question will be tested in English, Bangla and Banglish. The expected
facts will come from the approved fixture pack created in Day 2.

## Proposed restock suggestion rule

For demonstration purposes, suggest enough units to reach twice the configured
low-stock threshold:

```text
suggested quantity = max(0, (2 * low_stock_threshold) - current quantity)
```

The UI must label this as a review suggestion. The Product Owner may replace
this formula before Day 2; after fixture expectations are created, changing it
requires updating those expectations.

## Data and privacy boundary

- Use synthetic product, customer, order, expense and task data by default.
- Use no real credentials, payment data, phone numbers or customer email addresses.
- Keep one dedicated staging workspace and one approved demo account.
- Label fixture version, data source, observation time and fixed reference date.
- Keep SQLite pilot data and PostgreSQL staging data visibly separate.

## Roles

| Role | Proposed owner |
|---|---|
| Product Owner and final acceptance | Project owner (user) |
| Developer and technical operator | Codex with project owner executing credential-only steps |
| Independent reviewer | Teammate - name required |
| Merchant demo presenter | Project owner unless another name is supplied |

## Day 1 approval decisions

The Product Owner must fill or approve these four items before Day 2:

| Decision | Proposed value | Final value |
|---|---|---|
| Merchant type | Bangladeshi retail merchant with inventory | Approved |
| Target meeting | Second half of November 2026; use relative `T` dates until fixed | Approved planning window; exact date pending |
| Demo reference date | `2026-11-01`, displayed as fixture data date | Approved |
| Independent reviewer | One teammate who checks expected results and rehearses | Role approved; name to be assigned before Day 11 |

Approving the proposed workflow also approves the five questions, 30-day
inactivity window, low-stock rule, finance definition and review-only restock
formula above. Any requested change should be recorded here before Day 2.

## Day 1 exit checklist

- [x] Primary walkthrough written.
- [x] Five supported questions fixed for review.
- [x] Existing business definitions mapped to the demo.
- [x] Data/privacy boundary written.
- [x] Proposed responsibilities written.
- [x] Merchant type approved.
- [x] Meeting date or November window recorded.
- [x] Reference date recorded.
- [x] Independent-reviewer role recorded; name may be assigned later.
- [x] Product Owner marks Day 1 approved.

Day 2 is authorized. Its output is a versioned synthetic fixture pack and an
independently checkable expected-results sheet.

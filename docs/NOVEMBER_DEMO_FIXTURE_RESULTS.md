# November Demo - Day 2 Fixture Results

Status: **Day 2 approved by Product Owner on 2026-10-11**
Fixture version: `november-v1`
Reference date: `2026-11-01` (`Asia/Dhaka`)
Currency: BDT
Data classification: synthetic demonstration data

## What was created

The versioned pack at [`demo_fixtures/november_v1`](../demo_fixtures/november_v1)
contains inventory, customers, orders, expenses, tasks and three CSV preview
cases. It contains no real merchant/customer data or credentials.

## Independently calculated results

| Area | Expected result |
|---|---|
| Inventory | 12 variants: 5 normal, 5 low-stock and 2 out-of-stock; 7 total rows are at or below threshold |
| Suggested restock | 39 total units using the approved `2 * threshold` target |
| Reference-date orders | 2 included orders; BDT 5,000 revenue |
| Receipts / receivable | BDT 3,500 receipts; BDT 1,500 receivable |
| Average order value | BDT 2,500 |
| Dated expenses | BDT 800 |
| Receipts less dated expenses | BDT 2,700; labeled operational view, not profit/cash flow |
| Inactive customers | 3 (`CUST-002`, `CUST-004`, `CUST-005`), using dates before 2026-10-02 |
| Tasks needing attention | 4 open tasks, ordered by priority then fixture key |
| Valid preview | 1 changed, 1 new, 0 errors, 0 conflicts |
| Conflict preview | 1 deliberately stale conflict |
| Invalid preview | 1 acceptable new row, 2 errors (formula and duplicate key) |

The machine-readable source of truth is
[`expected-results.json`](../demo_fixtures/november_v1/expected-results.json).

## Verification performed

```text
November demo fixture pack is valid and expected results match.
Targeted pytest: 2 passed
Ruff: all checks passed
```

The validator recalculates results from the CSV files; it does not merely check
that expected values exist. It reuses the production CSV parser for preview
validation cases.

## Day 2 review checklist

- [x] Fixture version, reference date, timezone and currency recorded.
- [x] 12 representative inventory variants across two locations created.
- [x] Normal, low-stock and out-of-stock cases included.
- [x] Finance, inactive-customer and task results calculated.
- [x] Valid/change/new, conflict, formula and duplicate preview cases included.
- [x] Automated validator, focused tests and lint pass.
- [x] Product Owner accepts the synthetic names and expected figures.
- [ ] Reviewer name is assigned before the Day 11 independent review.
- [x] Product Owner marks Day 2 approved.

After approval, Day 3 will implement an idempotent, tenant-scoped PostgreSQL
seed command for this pack, plus a safe reset procedure and database-backed
verification. No staging data will be changed until that implementation is
reviewed and its execution is separately approved.

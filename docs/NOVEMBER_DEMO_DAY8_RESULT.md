# November Demo Day 8 Result

Date: 2026-10-12
State: Staging migration, seed and restricted-runtime verification complete;
awaiting Product Owner approval

## Implemented

- Added PostgreSQL tables for customers, orders, expenses and tasks.
- Every table carries a tenant ID, reviewed source/version metadata and an
  observation time.
- Forced Row-Level Security limits reads to the active tenant membership.
- The runtime role receives SELECT only; fixture writes require the temporary
  migration credential.
- Added deterministic readers for:
  - the reference-date financial summary;
  - the 30-day inactive customer cohort;
  - open tasks ordered by reviewed priority.
- Each reader checks its domain permission before opening a database transaction.
- Customer output contains pseudonymous customer keys and no contact details.
- Added one idempotent migration-and-seed command that uses the migration URL
  once, verifies counts, commits only after a rollback rehearsal, and removes
  the temporary credential afterward.

## Reviewed expected results

| Fact | Expected result |
|---|---:|
| Customers | 6 |
| Orders | 8 |
| Expenses | 3 |
| Tasks | 5 |
| 2026-11-01 sales orders | 2 |
| Revenue | BDT 5,000 |
| Receipts | BDT 3,500 |
| Receivable | BDT 1,500 |
| Dated expenses | BDT 800 |
| Receipts less dated expenses | BDT 2,700 |
| 30-day inactive customers | 3 |
| Tasks needing attention | 4 |

## Staging execution

After explicit approval and temporary migration URL configuration, run:

```powershell
.\.venv\Scripts\python.exe .\scripts\seed_november_demo_business_facts.py --action execute
```

This will apply migration `0005_demo_facts`, rehearse the seed in a rolled-back
transaction, apply it once, verify the fixture counts and remove the migration
credential. It does not rotate the API or authenticator database passwords.

## Execution evidence

Completed on 2026-10-12:

- Alembic upgraded `0004_import_preview` to `0005_demo_facts`.
- Rolled-back rehearsal: 6 customers, 8 orders, 3 expenses and 5 tasks.
- Committed seed: 6 customers, 8 orders, 3 expenses and 5 tasks.
- Temporary migration credential removed from `.env`.
- Restricted authenticator resolved the active owner membership.
- Restricted runtime role returned the reviewed finance summary, inactive keys
  `CUST-002`, `CUST-004`, `CUST-005`, and attention tasks `TASK-001` through
  `TASK-004`.

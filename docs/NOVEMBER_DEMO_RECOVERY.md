# November demo recovery and rollback

Status: candidate procedure for the synthetic November demonstration
Scope: Render web/API services and the dedicated Supabase staging workspace

## Before deployment

1. Record the candidate commit with `git rev-parse HEAD`.
2. Confirm GitHub Actions `offline-checks` passes for that exact commit.
3. Record the currently live Render commit for both web and API services.
4. Confirm the fixture version is `november-v1` and the workspace ID matches the
   dedicated staging workspace. Do not print database URLs or credentials.
5. Open Inventory through the existing account and record the expected baseline:
   12 variants, 7 at/below threshold, including 2 out of stock.

## Application rollback

If the candidate fails after deployment:

1. In Render, open each affected service and redeploy the previously recorded
   live commit. Roll back API first, then web, so the old web never depends on a
   newer unavailable API contract.
2. Wait for `/health/live` on the API and `/` on the web service.
3. Sign in once and verify Inventory. Do not bypass Auth0 or workspace checks.
4. Record the failed candidate SHA, restored SHA, timestamps and sanitized
   correlation IDs. Never copy session cookies, bearer tokens or database URLs.

The Day 9-12 changes add read-only endpoints and UI. They contain no schema
downgrade and no application write action, so application rollback does not
require deleting tenant data.

## Synthetic demo data recovery

The demo database state is reproducible from reviewed migrations and the
versioned `november-v1` fixtures. This is the recovery path available on the
current student-funded setup:

1. Configure the Supabase Session pooler migration URL temporarily in `.env`.
2. Run the inventory seed in rollback rehearsal and apply mode:

   ```powershell
   .\.venv\Scripts\python.exe .\scripts\seed_november_demo_inventory.py --action execute
   ```

3. Reconfigure the temporary migration URL because the command removes it.
4. Run the business-facts migration/seed command:

   ```powershell
   .\.venv\Scripts\python.exe .\scripts\seed_november_demo_business_facts.py --action execute
   ```

5. Capture a fresh authenticated session only if the existing one has expired,
   then verify Inventory and the five Copilot questions.

Both commands rehearse with rollback, verify counts before commit and remove the
migration credential. They update only the dedicated fixture records and refuse
unsafe workspace/configuration values.

## Recovery limits

This reconstruction procedure is suitable for synthetic demo data. It is not a
complete PostgreSQL backup and does not recover unrelated tenant records, audit
history, external objects or point-in-time state. A production pilot requires a
managed encrypted backup, separate backup credentials, retention policy and an
isolated restore test. That paid operational control remains deferred.

## Post-recovery acceptance

- API and web report healthy.
- Login and active workspace authorization succeed.
- Inventory shows 12 variants, 7 at/below threshold and 2 out of stock.
- Finance shows BDT 5,000 revenue, BDT 3,500 receipts and BDT 800 expenses.
- Inactive customers are `CUST-002`, `CUST-004`, `CUST-005`.
- Four tasks need attention.
- Restock proposal totals 39 suggested units and remains review-only.
- No secrets or private error details appear in evidence or ordinary logs.

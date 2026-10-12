# November Demo - Day 3 Inventory Seed Runbook

Status: **Implemented and executed on staging on 2026-10-12**

## What the command does

[`seed_november_demo_inventory.py`](../scripts/seed_november_demo_inventory.py)
loads the approved `november-v1` inventory fixture into the configured staging
workspace using the migration credential. It:

- derives stable UUIDs from workspace ID and fixture business keys;
- tags every managed row with source `bizpilot-november-demo` and version
  `november-v1`;
- refuses SKU/location collisions with unrelated workspace data;
- creates or updates only the fixture's locations, products, variants and balances;
- keeps a balance's record version unchanged when quantity/threshold are unchanged;
- verifies 12 variants, 7 low-stock and 2 out-of-stock rows before commit;
- suppresses raw database errors and removes the migration URL from `.env` after use.

The seed does not create inventory movements because it is controlled demo
setup performed before merchant use. Later inventory changes require their own
reviewed workflow and movement records.

## Commands

Configure `BIZPILOT_MIGRATION_DATABASE_URL` in `.env` immediately before each
administrative command. The tool removes it after connecting.

Dry-run the actual SQL and roll back:

```powershell
.\.venv\Scripts\python.exe .\scripts\seed_november_demo_inventory.py --action plan
```

Run the approved plan and apply sequence with one temporary credential:

```powershell
.\.venv\Scripts\python.exe .\scripts\seed_november_demo_inventory.py --action execute
```

`execute` runs and rolls back the first transaction, checks the reviewed counts,
then repeats and commits in a second transaction. If either validation fails,
the apply does not complete.

Apply and commit the reviewed seed:

```powershell
.\.venv\Scripts\python.exe .\scripts\seed_november_demo_inventory.py --action apply
```

Verify an applied seed without changing it:

```powershell
.\.venv\Scripts\python.exe .\scripts\seed_november_demo_inventory.py --action verify
```

Reset requires the exact configured workspace UUID as an explicit argument:

```powershell
.\.venv\Scripts\python.exe .\scripts\seed_november_demo_inventory.py `
  --action reset `
  --confirm-workspace <exact-BIZPILOT_WORKSPACE_ID>
```

Reset deletes only matching source/version rows, in dependency order. It
refuses deletion if any matching balance has inventory movement history.
Unrelated tenant or workspace rows are outside every delete predicate.

## Staging execution sequence

1. Product Owner approves Day 3 staging execution.
2. Configure the Supabase Session pooler migration URL without displaying it.
3. Run `--action execute`; require matching `planned` and `applied` counts and
   `Database changes committed: True`.
4. Reconfigure the URL only if a separate `--action verify` run is required.
5. Open inventory through the normal authenticated web application and compare
   the visible summary with the reviewed values.

Do not paste the URL, password or command output containing credentials into
chat, screenshots or evidence. The command itself never prints the URL.

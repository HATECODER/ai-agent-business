# November Demo - Day 3 Staging Inventory Result

Status: **Approved by Product Owner on 2026-10-12**
Executed: 2026-10-12 (Asia/Dhaka)
Fixture: `november-v1`
Workspace: configured `BizPilot Staging Merchant` workspace

## Result

The approved combined seed command completed against Supabase staging.

| Check | Result |
|---|---|
| Rollback-only plan | 12 variants, 7 threshold-matching rows including 2 out-of-stock |
| Committed apply | 12 variants, 7 threshold-matching rows including 2 out-of-stock |
| Reviewed fixture totals | Exact match |
| Authenticated Inventory UI | 12 variants, 5 low-stock and 2 out-of-stock; Product Owner visually verified |
| Database commit | Completed |
| Migration credential cleanup | Removed from local `.env` |
| Render API health after seed | HTTP 200, `status: ok` |

No raw database URL, password or tenant UUID is recorded in this evidence.

## Implemented controls

- Stable IDs make repeated fixture execution deterministic.
- A rerun does not duplicate fixture locations, products, variants or balances.
- Unchanged quantities and thresholds retain their record version.
- Source/version predicates isolate the fixture from unrelated workspace rows.
- SKU or location collisions with unrelated data stop the operation.
- Reset requires the exact workspace ID and refuses balances with movement history.
- The tool verifies the reviewed inventory counts before committing.

## Day 3 acceptance checklist

- [x] Day 2 fixture is the seed source.
- [x] Rollback-only transaction completed with reviewed counts.
- [x] Apply transaction committed with the same counts.
- [x] Credential removed after the administrative operation.
- [x] Deployed API remained healthy after seeding.
- [x] Reset procedure documented.
- [x] Product Owner visually confirms the authenticated Inventory page shows
      12 variants, 5 low-stock and 2 out-of-stock. The UI excludes the two
      out-of-stock rows from its low-stock card, while database verification
      reports seven total rows at or below threshold.
- [x] Product Owner marks Day 3 accepted.

After acceptance, Day 4 selects and reviews the staging malware-scanner adapter.
That decision includes hosting, private connectivity, timeout behavior,
signature freshness and fail-closed operation before CSV preview is enabled.

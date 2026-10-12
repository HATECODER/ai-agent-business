# November Demo Day 5 Result

Date: 2026-10-12
State: Awaiting Product Owner approval

## Delivered at zero additional hosting cost

- The commercial API now has a dormant ClamAV configuration path.
- `BIZPILOT_IMPORT_PREVIEW_ENABLED=false` is explicit in the staging Blueprint.
- Missing, incomplete or invalid scanner configuration keeps preview unavailable.
- No ClamAV service was added to the Blueprint and no paid resource was created.
- Expired preview and error metadata can be removed with an operator-controlled
  maintenance command; associated error rows are deleted by the database cascade.
- The maintenance command requires a temporary migration credential and removes
  that credential from the local `.env` after an execution attempt.

## Future funded activation

After private ClamAV deployment and its separate approval, configure these
server-only values on the API:

```text
BIZPILOT_IMPORT_PREVIEW_ENABLED=true
BIZPILOT_CLAMAV_HOST=<private-service-host>
BIZPILOT_CLAMAV_PORT=3310
BIZPILOT_CLAMAV_TIMEOUT_SECONDS=5
```

Enabling these settings is not sufficient by itself for production readiness.
The deferred signature freshness, rate limit, proxy limit and browser rendering
checks in Decision 0011 must also pass.

## Cleanup command

After temporarily configuring `BIZPILOT_MIGRATION_DATABASE_URL` locally:

```powershell
.\.venv\Scripts\python.exe .\scripts\purge_expired_inventory_previews.py --execute
```

The script reports only the deletion count and never prints the credential.

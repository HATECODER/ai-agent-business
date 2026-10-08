# BizPilot restricted pilot runbook

## Ownership and communication

- **Release owner:** the product owner who approves the Day 3 release record.
- **Business-hours operator:** **TBD before hosted release**. Record a named person and contact route in the release record.
- **Data classification:** fictional `fictional-v1` data only. Stop the pilot if real customer data appears.

## Provider outage or 401/403/429

1. Read the sanitized error category and run ID; do not log prompts, tool payloads or keys.
2. Check Google AI Studio project/API status and quota. Rotate a rejected or exposed key in Render.
3. Do not repeatedly replace keys or silently switch providers.
4. If evaluation must continue without a model, set `BIZPILOT_AI_MODE=offline`, redeploy, and retain the visible offline label. Dashboard calculations remain deterministic.

## Daily budget exhausted

1. Confirm usage in the Copilot caption and `ai_usage`; keep `unknown` reservations until reconciled.
2. Do not raise `BIZPILOT_DAILY_BUDGET_USD` without release-owner approval.
3. Continue with deterministic dashboard/offline flows or wait for the next Bangladesh calendar day.

## Failed startup

1. Check Render logs for missing OIDC environment names, missing database, invalid data mode or schema errors.
2. Run `python scripts/write_streamlit_secrets.py` and `python scripts/pilot_preflight.py` in the service shell. Neither command prints secret values.
3. Confirm `/var/data/bizpilot.sqlite3` exists and `BIZPILOT_DB_PATH` points to it.
4. If the initial seed hook failed, keep access disabled and rerun `python -m database.seed` once from the disk-backed service shell.

## Disable access immediately

1. Set `BIZPILOT_OWNER_SUBJECTS` to an empty value and redeploy, or enable Render maintenance mode.
2. Revoke the Google OAuth client secret or Gemini key if compromised.
3. Preserve the database and logs for review; do not delete evidence.

## Backup and restore

1. Run the online backup command from `docs/PILOT_DEPLOYMENT.md`.
2. Restore to a new filename and verify logical counts/digests.
3. Stop the service before changing `BIZPILOT_DB_PATH` to the restored file. Keep the former database for rollback.
4. Start the service, run preflight, sign in, and verify inventory, one confirmed task, audit state and usage state.

## Application rollback

1. Create and verify a database backup before rollback.
2. In Render, redeploy the previously tested commit/artifact. Do not run a destructive schema downgrade.
3. Run preflight and the representative login → inventory → approval → replay-safe task flow.
4. Record commit IDs, start/end time, downtime and result. Render disk-backed services do not provide zero-downtime deploys.

## Release stop conditions

- Authentication or allowlist bypass.
- Missing persistent state after restart.
- Failed restore comparison.
- Secret exposure or reachable high/critical security finding.
- Incorrect financial facts or any unconfirmed external/internal mutation.
- Live evaluation below the acceptance threshold.

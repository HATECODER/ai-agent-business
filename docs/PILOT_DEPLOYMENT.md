# Restricted pilot deployment

## Chosen deployment shape

- **Host:** Render web service in Singapore.
- **Runtime:** the repository `Dockerfile`, Python 3.13.2, one instance.
- **Storage:** 1 GB persistent disk mounted at `/var/data`; SQLite path `/var/data/bizpilot.sqlite3`.
- **Identity:** Google OIDC through Streamlit, followed by the server-side `issuer|subject` allowlist.
- **Model:** `gemini-3.1-flash-lite`, fictional data only, USD 2/day application budget.

Render documents that only files below the disk mount persist, that a disk limits the service to one instance, and that disk-backed deploys have a short interruption. Persistent disk use therefore matches this two-evaluator SQLite pilot but is not a scale-out architecture. See [Render persistent disks](https://render.com/docs/disks). The Blueprint fields are based on the current [Render Blueprint specification](https://render.com/docs/blueprint-spec).

## Before deployment

1. Revoke every API key previously pasted into chat or screenshots. Create a new Gemini key and keep it only in Render's secret settings.
2. Push the reviewed commit to the repository connected to Render. CI must pass before deployment.
3. In Google Cloud, configure an OAuth Web client and consent screen. Google requires the redirect URI to match exactly; use `https://<service-host>/oauth2callback`. See [Google OpenID Connect](https://developers.google.com/identity/openid-connect/openid-connect).
4. Limit the Google OAuth test-user list to the intended evaluators while the consent screen is in testing mode.

## Create the Render service

1. In Render, create a Blueprint from this repository's `render.yaml`.
2. Review the billable `0.5c-512mb` service and 1 GB disk before accepting it. A persistent disk is unavailable on the free service shape.
3. Enter these secret values when prompted:

   - `BIZPILOT_PUBLIC_URL`: exact HTTPS origin, without a trailing path.
   - `GEMINI_API_KEY`: newly rotated synthetic-evaluation key.
   - `OIDC_CLIENT_ID` and `OIDC_CLIENT_SECRET`: Google OAuth Web client values.
   - `BIZPILOT_OWNER_SUBJECTS`: leave empty for the first authenticated identification step, or enter one/two known `https://accounts.google.com|<sub>` identifiers.

4. Confirm the generated `OIDC_COOKIE_SECRET` is present. Do not copy it into source control.
5. Deploy. `/_stcore/health` checks the Streamlit process. The one-time `initialDeployHook` explicitly provisions `fictional-v1` on the persistent disk. Application pilot startup itself remains fail closed when that database is absent.

## Bootstrap evaluator identities

1. Open the HTTPS service and sign in with an intended Google test account.
2. If the account is not allowlisted, the app stops before database access and displays that signed-in user's own `issuer|subject` identity.
3. Copy at most two such identifiers into `BIZPILOT_OWNER_SUBJECTS`, separated by semicolons, and redeploy.
4. In the Render Shell, run `python scripts/pilot_preflight.py`. Every line must report `PASS`; it does not print keys or identity values.

## Required deployed checks

Record results in the release file rather than marking a check passed from configuration alone.

1. Valid evaluator login reaches the synthetic dashboard.
2. A non-allowlisted Google account stops before any dashboard/database/model access.
3. Direct page access without login shows only the sign-in gate.
4. Logout removes access; refresh and another tab also require authentication.
5. An expired application session is rejected.
6. Removing an evaluator from `BIZPILOT_OWNER_SUBJECTS` blocks their next action.
7. Create and confirm one internal task, restart the service, and confirm the task remains.
8. Run one live Gemini smoke and confirm the deterministic dashboard remains usable during a simulated provider failure.

Streamlit's OIDC setup and `st.login` behavior are documented in [Streamlit authentication](https://docs.streamlit.io/develop/concepts/connections/authentication).

## Backup and restore on Render

Create a consistent online backup on the persistent disk:

```bash
python scripts/manage_backup.py backup \
  --source /var/data/bizpilot.sqlite3 \
  --output /var/data/backups/bizpilot-YYYYMMDD-HHMMSS.sqlite3
```

Restore to a separate path and verify it:

```bash
python scripts/manage_backup.py restore \
  --backup /var/data/backups/bizpilot-YYYYMMDD-HHMMSS.sqlite3 \
  --target /var/data/restore-check.sqlite3
python scripts/manage_backup.py verify --database /var/data/restore-check.sqlite3
```

The tool uses Python's `sqlite3.Connection.backup` API and compares logical table digests. Never overwrite the active database during a restore test. See the [Python SQLite backup API](https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.backup).

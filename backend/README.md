# BizPilot commercial backend

This package is the FastAPI foundation for the commercial multi-tenant product.
The existing root Streamlit application remains the fictional evaluation demo.

Current implemented boundary:

- liveness endpoint with no environment or tenant details;
- fixed R1 merchant roles and permission grants;
- active tenant resolved from an exact active membership;
- tenant and own-record authorization checks with sanitized denial messages;
- two-tenant, revoked-membership, and role-denial tests.
- Alembic-managed PostgreSQL tenant, identity, membership, location, platform-staff, and audit tables;
- a restricted `bizpilot_runtime` role with tenant Row-Level Security;
- transaction-local tenant/identity/membership/version database context;
- real PostgreSQL isolation tests in CI.
- managed OIDC bearer validation with fixed `RS256`, exact issuer/audience,
  expiry, issued-at, subject, token-age, and JWKS checks;
- a separate restricted PostgreSQL authenticator role and persistent
  identity/membership lookup on every protected request;
- identity suspension/revocation and `tokens_valid_after` session invalidation;
- a protected `GET /api/v1/workspace` authority endpoint with sanitized denial
  responses, categories, and server-generated correlation IDs.
- tenant-isolated product, variant, inventory balance, and movement schemas with
  composite tenant keys and forced RLS;
- a permission-protected, bounded `GET /api/v1/inventory` endpoint with
  low-stock filtering, UUID cursor pagination, and source/freshness evidence;
- read-only runtime privileges for inventory and locations. Inventory adjustment
  and import apply remain disabled;
- a preview-only inventory CSV API with strict UTF-8/schema/size/row validation,
  deterministic new/change/conflict/unchanged counts, tenant-scoped expiring
  metadata, and formula-safe error CSVs;
- a mandatory injected malware-scanner boundary. Without a reviewed scanner,
  preview fails closed with `503`; raw CSV bytes are never persisted.
- workspace capability discovery returns the active role's permission names for
  the separate merchant UI; it never replaces endpoint authorization.

Run locally after installing the root locked requirements:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8000
```

For a dedicated PostgreSQL database, provision the non-login roles first and
then run the migration with a protected migration credential:

```powershell
psql "$env:BIZPILOT_DATABASE_URL" -f backend/sql/roles.sql
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
```

The normal API connection must use a login permitted to `SET ROLE
bizpilot_runtime`; it must not own tables or have `BYPASSRLS`. Never put a
database credential in `alembic.ini`, source control, logs, or browser code.

Configure the protected merchant API with secret-manager values:

```text
BIZPILOT_AUTH_DATABASE_URL=postgresql+psycopg://<auth-login>:<secret>@<host>/<db>
BIZPILOT_OIDC_ISSUER=https://<managed-idp-issuer>/
BIZPILOT_OIDC_AUDIENCE=<commercial-api-audience>
BIZPILOT_OIDC_JWKS_URL=https://<managed-idp-host>/.well-known/jwks.json
```

The auth login may assume only `bizpilot_authenticator`; the normal API login
may assume only `bizpilot_runtime`. The `X-BizPilot-Tenant` request header is a
workspace selector and never an authorization credential. No production IdP or
database credential is stored in this repository.

The Phase 1C identity boundary does not implement browser login/cookies,
Platform Admin access, or merchant invitations. See
[Decision 0005](../docs/decisions/0005-phase1-managed-identity.md).

Phase 1D adds the first read-only inventory API. It does not accept merchant
files or expose inventory writes. See
[Decision 0006](../docs/decisions/0006-phase1-inventory-read-foundation.md).

Phase 1E adds the staged validation and preview contract. The default app keeps
it unavailable until a reviewed malware scanner is injected, and no import
apply endpoint exists. See
[Decision 0007](../docs/decisions/0007-phase1-inventory-import-preview.md) and
the [CSV template](../docs/templates/inventory-import-template.csv).

Phase 1F adds the separate merchant inventory interface under
[`apps/web`](../apps/web/README.md). It remains disconnected until the managed
browser-session/BFF checkpoint is accepted. See
[Decision 0008](../docs/decisions/0008-phase1-merchant-inventory-ux.md).

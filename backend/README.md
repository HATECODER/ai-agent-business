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

This checkpoint does not yet validate managed OIDC tokens or expose protected
business HTTP endpoints.

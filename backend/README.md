# BizPilot commercial backend

This package is the FastAPI foundation for the commercial multi-tenant product.
The existing root Streamlit application remains the fictional evaluation demo.

Current implemented boundary:

- liveness endpoint with no environment or tenant details;
- fixed R1 merchant roles and permission grants;
- active tenant resolved from an exact active membership;
- tenant and own-record authorization checks with sanitized denial messages;
- two-tenant, revoked-membership, and role-denial tests.

Run locally after installing the root locked requirements:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8000
```

This checkpoint does not yet validate OIDC tokens or connect to PostgreSQL.

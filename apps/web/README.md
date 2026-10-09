# BizPilot merchant web

This is the commercial Next.js interface. It is separate from the fictional
Streamlit demo at the repository root.

Phase 1F implements the inventory presentation and capability boundary:

- merchant labels instead of database IDs;
- responsive stock table, search, attention filter, status and freshness;
- role-aware import visibility based on server-provided permission names;
- downloadable UTF-8 CSV template and an honest preview-only workflow;
- a fail-closed screen while the managed browser-session adapter is absent.

It deliberately does not read a bearer token from browser storage, create an
OIDC session, call the preview endpoint, or apply inventory changes. Those
controls require a reviewed server-side managed-session/BFF boundary.

```powershell
cd apps/web
npm ci
npm test
npm run typecheck
npm run build
npm run dev
```

Open `http://localhost:3000/inventory`. The current page shows the secure
configuration state and disabled actions without synthetic merchant records.

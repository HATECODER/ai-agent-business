# BizPilot merchant web

This is the commercial Next.js interface. It is separate from the fictional
Streamlit demo at the repository root.

Phase 1F implements the inventory presentation and capability boundary. Phase
1G adds the first managed browser-session/BFF boundary:

- merchant labels instead of database IDs;
- responsive stock table, search, attention filter, status and freshness;
- role-aware import visibility based on server-provided permission names;
- downloadable UTF-8 CSV template and an honest preview-only workflow;
- Auth0 Universal Login with an encrypted HTTP-only, SameSite session cookie;
- server-only access-token forwarding to the FastAPI API;
- one server-configured active workspace, so browser input cannot grant tenant authority;
- live inventory read and same-origin CSV preview forwarding;
- a nonce-based Content Security Policy on application routes;
- a fail-closed screen whenever identity, workspace, or API configuration is absent.

The browser cannot call an access-token endpoint and does not receive or store
the OIDC bearer token. Inventory apply remains unavailable.

Configure the server-only values shown in the repository `.env.example`. For
local development, register `http://localhost:3000/auth/callback` and
`http://localhost:3000` as the Auth0 callback and logout URL. Production must
use exact HTTPS origins. `AUTH0_SECRET` is 32 random bytes encoded as 64 hex
characters. The FastAPI OIDC issuer/audience settings must match the Auth0 API.

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

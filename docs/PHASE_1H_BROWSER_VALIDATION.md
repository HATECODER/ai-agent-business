# Phase 1H Auth0 Staging and Real-Browser Validation

## Status

In progress. The local unauthenticated browser-security suite passes. Real
Auth0 staging configuration and authenticated validation are blocked until the
Product Owner provisions the staging application, API, database and secrets.

## Safety rules

- Do not paste Auth0 client secrets, cookie secrets, database URLs, passwords,
  OTPs, browser-state files or access tokens into chat, screenshots, issues,
  commits or test output.
- The Product Owner completes Auth0 authentication manually.
- Keep `playwright/.auth/merchant.json` local and delete it after the validation
  session expires. It can impersonate the test account while valid.
- Use a dedicated staging merchant account and sanitized data.
- Do not enable inventory apply, messaging, payments or real merchant upload.

## Prerequisites

1. Exact HTTPS staging application and API origins.
2. Auth0 Regular Web Application with exact callback
   `https://<app-host>/auth/callback` and logout URL
   `https://<app-host>`.
3. Auth0 API audience matching `AUTH0_AUDIENCE` and
   `BIZPILOT_OIDC_AUDIENCE`.
4. FastAPI issuer `https://<AUTH0_DOMAIN>/` and JWKS URL
   `https://<AUTH0_DOMAIN>/.well-known/jwks.json`.
5. One active staging identity, merchant membership, role and workspace UUID.
6. Separate PostgreSQL migration/runtime/authenticator credentials.
7. Deployed Next.js and FastAPI services with server-only secrets.

Run `npm run staging:preflight` from `apps/web`. It reports only missing or
invalid setting names and never prints values.

## Automated checks

### Signed-out checks

Run `npm run browser:security`.

The command builds and serves the production application before launching the
browser. The CSP check therefore uses the production policy.

- inventory fails closed without a session;
- no fictional inventory appears;
- CSV preview remains disabled;
- CSP, frame denial, MIME sniffing and browser capability headers are present;
- no token appears in local storage, session storage or script-readable
  cookies;
- `/auth/access-token` does not return a token;
- a cross-origin preview request is never accepted.

### Authenticated checks

Set `BIZPILOT_BROWSER_BASE_URL` to the exact HTTPS staging origin. Run
`npm run browser:auth:capture`, complete login manually, then run
`npm run browser:authenticated`.

- the managed merchant reaches the server-selected workspace;
- the session cookie is HTTP-only, Secure on HTTPS and SameSite=Lax;
- internal database identifiers are absent from the rendered page;
- two tabs share the managed session without exposing a token;
- a cross-origin preview request is rejected.

## Manual security matrix

Record timestamp, tester, staging release SHA, result and a redacted evidence
reference for every row. Never record cookies, tokens or customer data.

| Test | Expected result | Status |
|---|---|---|
| Valid login | Returns to `/inventory`; authorized workspace loads | Pending |
| Invalid callback/state | Callback rejected; no local session created | Pending |
| Logout | Application session removed; protected page fails closed | Pending |
| Expired eight-hour session | Reauthentication required | Pending |
| Auth0/back-channel revocation | Existing session loses access within the accepted window | Pending |
| Suspended identity | Next API request denied | Pending |
| Removed membership | Next API request denied | Pending |
| Role/permission change | Next request uses current server grants | Pending |
| Wrong workspace ID | Membership resolution denies access | Pending |
| Direct FastAPI without bearer | `401` sanitized response | Pending |
| Cross-tenant object attempt | No data or existence disclosure | Pending |
| CSRF preview request | Exact-origin check rejects request | Pending |
| XSS payload in CSV fields | Rendered as text or rejected; CSP remains effective | Pending |
| Multiple tabs | No token exposure or cross-user state bleed | Pending |
| Oversized upload at edge | Rejected before application multipart parsing | Pending |
| Provider/API outage | Sanitized unavailable state; no secret in logs/UI | Pending |

## Exit gate

Phase 1H can be accepted only when:

- staging preflight passes;
- signed-out and authenticated automated suites pass;
- every applicable manual row has redacted evidence;
- logout, expiry, membership revocation and role-change behavior are confirmed;
- CSP and CSRF checks pass in the deployed HTTPS environment;
- no access token, secret, internal database ID or private data appears in
  browser storage, UI, screenshots or normal logs;
- remaining edge upload and malware-scanner blockers stay explicitly disabled.

After acceptance, remove the saved browser state and proceed to
`ONE_WEEK_PLAN.md`.

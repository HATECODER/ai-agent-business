# Phase 1H Auth0 Staging and Real-Browser Validation

## Status

In progress. Auth0, Supabase, Render HTTPS staging, the synthetic Owner
membership and the authenticated browser boundary are configured. On
2026-10-10 the deployed authenticated suite passed 5/5 checks: selected
workspace access, secure session-cookie/browser-storage handling, two-tab
isolation, logout fail-closed behavior and cross-origin preview rejection.
The remaining provider-revocation and failure-path rows must pass before Phase
1H acceptance. Immediate membership revocation and role-change checks passed
against the deployed HTTPS application on 2026-10-11, and the harness restored
the test identity to active Owner authority afterward. The captured application
cookie had the configured eight-hour absolute lifetime, and a browser context
with that cookie expired was required to reauthenticate.

Provider-initiated back-channel logout is a confirmed blocker. The installed
Auth0 SDK exposes `/auth/backchannel-logout`, but it requires a shared session
store implementing logout-token deletion. The current encrypted stateless
cookie configuration has no such store, and the deployed endpoint failed
closed with HTTP 500 on 2026-10-11. Phase 1H must not claim Auth0 revocation
until a protected shared session store is implemented and a real signed logout
event invalidates the captured browser session.

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
| Valid login | Returns to `/inventory`; authorized workspace loads | Passed 2026-10-10; deployed HTTPS authenticated suite |
| Invalid callback/state | Callback rejected; no local session created | Passed 2026-10-11; rejected callback granted no authenticated access |
| Logout | Application session removed; protected page fails closed | Passed 2026-10-10; deployed HTTPS authenticated suite |
| Expired eight-hour session | Reauthentication required | Passed 2026-10-11; configured lifetime confirmed and expired cookie rejected |
| Auth0/back-channel revocation | Existing session loses access within the accepted window | Blocked: stateless SDK session has no logout-token session store; endpoint fails closed |
| Suspended identity | Next API request denied | Pending |
| Removed membership | Next API request denied | Passed 2026-10-11; active browser session denied on next request |
| Role/permission change | Next request uses current server grants | Passed 2026-10-11; Viewer permissions applied, then Owner restored |
| Wrong workspace ID | Membership resolution denies access | Pending |
| Direct FastAPI without bearer | `401` sanitized response | Passed 2026-10-11; generic detail and Bearer challenge |
| Cross-tenant object attempt | No data or existence disclosure | Pending |
| CSRF preview request | Exact-origin check rejects request | Passed 2026-10-10; cross-origin request returned rejection |
| XSS payload in CSV fields | Rendered as text or rejected; CSP remains effective | Pending |
| Multiple tabs | No token exposure or cross-user state bleed | Passed 2026-10-10; no script-readable token |
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

# Phase 1H Auth0 Staging Validation Evidence — 2026-10-11

## Scope

- Render HTTPS web and API staging services at release `e20a541`.
- Auth0 Regular Web Application and custom API.
- Supabase PostgreSQL with migrations `0001`–`0004` and restricted runtime/authenticator roles.
- Dedicated synthetic Auth0 database test user and synthetic merchant workspace.
- No real merchant data, inventory apply, messaging, payment or publishing capability.

## Passed evidence

| Check | Result |
|---|---|
| Public web/API readiness | Both returned HTTP 200 after free-tier wake-up |
| Restricted membership lookup | Configured identity resolved as active Owner through authenticator role |
| Authenticated browser suite | 8/8 passed against deployed HTTPS staging |
| Valid login/workspace | Server-selected workspace loaded; internal database IDs absent |
| Session cookie | HTTP-only, Secure and SameSite=Lax; approximately eight-hour configured lifetime |
| Browser storage | No access or ID token in local/session storage or script-readable cookie |
| Multiple tabs | Same managed identity without script-readable token |
| Logout | Application session removed and inventory failed closed |
| Expired cookie | Protected page required reauthentication |
| Invalid callback/state | Callback failed and an empty browser context received no authenticated access |
| Direct API without bearer | Sanitized HTTP 401 with Bearer challenge |
| Cross-origin preview | Rejected with HTTP 403 |
| Membership revocation | Existing browser session denied on its next request |
| Role change | Existing session applied Viewer grants immediately; Owner was restored afterward |
| Credential cleanup | Temporary migration credential removed after each administrative operation |

## Security incident during validation

One failed test assertion included an encrypted application session cookie in
the local test output. The value is not reproduced in this record. Response:

1. deleted the captured browser state, trace, screenshots and generated test results;
2. set the staging identity `tokens_valid_after` cutoff to invalidate earlier access tokens;
3. rotated the application cookie encryption secret twice because the first replacement was visible in IDE context;
4. redeployed the web service and captured a new dedicated test session;
5. changed the failing assertion so it never includes cookie objects in failure output;
6. reran the corrected deployed suite, which passed 8/8;
7. retained no credential, cookie or token in this evidence file.

## Open blockers and unclaimed rows

| Item | State / required work |
|---|---|
| Auth0 back-channel logout | **Blocked.** Current encrypted stateless sessions have no shared session store implementing logout-token deletion. The SDK endpoint fails closed with HTTP 500. Implement a protected shared session store, configure Auth0 back-channel logout, and prove a signed event invalidates an existing browser session. |
| Wrong workspace and cross-tenant object | Existing unit/PostgreSQL coverage passes, but deployed bearer-token adversarial evidence is still required. Keep the fixed server-selected workspace and do not expose tokens to the browser. |
| XSS CSV rendering | Apply is disabled and deployed preview processing is not enabled. Run payload rendering tests when the reviewed preview service is enabled. |
| Oversized upload at edge | Edge rejection before multipart parsing is not implemented/proven; keep real upload disabled. |
| Provider/API outage | Free-tier cold-start unavailable state was observed and sanitized, but a controlled outage/log-redaction exercise remains. |
| Wider production operations | Shared session store, paid always-on hosting, monitoring, backup/restore and incident drill remain outside this staging checkpoint. |

## Release decision

Phase 1H is **not yet accepted** because back-channel revocation is an explicit
exit requirement and is unsupported by the current stateless session design.
The authenticated BFF, membership revocation, role-change, expiry, callback,
logout and browser-token boundaries have deployed evidence. Proceed only with
the restricted demonstration boundary while the listed features stay disabled;
do not describe this staging environment as production-ready.

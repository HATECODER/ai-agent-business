# Phase 1H Auth0 Staging Validation Evidence — 2026-10-11

## Scope

- Render HTTPS web and API staging services through release `f2ac444`.
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
| Stateful session storage | AES-256-GCM encrypted sessions used the same-region Render private network; public Redis access remained disabled |
| Auth0 back-channel logout | A real signed Account Deactivated event invalidated the captured Redis-backed browser session |
| Suspended identity | The blocked test identity failed closed; it was unblocked after validation |
| Wrong workspace | A valid but unassigned workspace UUID was denied without data or internal-ID disclosure; the original Owner workspace was restored and reverified |
| CSV XSS payload | The deployed preview path failed closed with a generic response; no payload-created script, image or dialog appeared |
| Oversized upload | The deployed BFF rejected the declared oversized multipart request with HTTP 413 before multipart parsing |
| API unavailable state | A Render cold start showed only the sanitized unavailable state, then recovered to HTTP 200 without configuration disclosure |
| Credential cleanup | Temporary migration credential removed after each administrative operation |
| Session cleanup | Captured browser state and temporary verification artifacts were deleted after validation |

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
| Cross-tenant object | Not applicable to the current browser surface because no object-detail route or bearer-token surface exists. PostgreSQL RLS integration tests cover tenant isolation; add deployed adversarial evidence when such a route is introduced. |
| CSV preview enablement | The deployed preview service deliberately fails closed until a reviewed malware scanner adapter is configured. Payload rejection was proven; preview and apply remain disabled. |
| Wider production operations | Paid persistent session hosting, monitoring, backup/restore and an incident drill remain outside this staging checkpoint. |

## Release decision

Phase 1H is **accepted for the restricted staging boundary**. The authenticated BFF, stateful session revocation, suspended
identity, membership revocation, role-change, wrong-workspace denial, expiry,
callback, logout and browser-token boundaries have deployed evidence.
The object-specific cross-tenant row is not applicable until an object-detail
surface exists. Proceed only with the restricted demonstration boundary while
the listed features stay disabled; do not
describe this staging environment as production-ready.

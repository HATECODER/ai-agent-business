# Decision 0009: Phase 1 Managed Browser Session and BFF

Date: 2026-10-09

## Status

Accepted by the Product Owner on 2026-10-09.

## Implemented boundary

- The commercial Next.js application uses the exact-version-pinned Auth0
  Next.js SDK as its managed OIDC browser-session adapter.
- Auth0 Universal Login owns the authorization-code transaction. The
  application receives an encrypted HTTP-only, SameSite session cookie with an
  eight-hour absolute lifetime. Rolling sessions are disabled in this first
  boundary.
- The SDK access-token browser endpoint is explicitly disabled. Only server
  code retrieves the OIDC access token and forwards it to FastAPI.
- The active Phase 1 workspace UUID and merchant-facing workspace name are
  server configuration. Browser fields, query parameters, headers, and upload
  values cannot choose tenant authority.
- Every BFF read still reaches FastAPI, where token validation, current
  identity/membership resolution, permission checks, and PostgreSQL RLS remain
  authoritative.
- The dynamic inventory page reads at most 100 rows with `no-store`, an
  eight-second upstream deadline, and sanitized signed-out, denied, and
  unavailable states.
- The BFF removes internal product, variant, location, balance, record-version,
  and source identifiers before serializing inventory to the React client.
- Authorized users can submit one CSV to the existing preview-only endpoint.
  The BFF requires an exact same-origin request, an active managed session, and
  bounded file metadata before forwarding it. The browser receives the
  controlled preview result, never the access token.
- Application routes receive a per-request nonce Content Security Policy.
  Existing response headers continue to deny framing and unnecessary browser
  capabilities.
- Inventory apply/write remains absent.

## Configuration contract

Server-only configuration is documented in `.env.example` and
`apps/web/README.md`. Production application and API base URLs must be exact
HTTPS origins. Local HTTP is accepted only for `localhost` or `127.0.0.1` in a
non-production process. The workspace selector must be a UUID and the Auth0
cookie secret must be 32 bytes encoded as 64 hexadecimal characters.

The Auth0 application must register the exact `/auth/callback` callback and
application logout URL. The FastAPI issuer and audience must match the Auth0
API configuration.

## Security review

This boundary follows Auth0's token-mediating backend mode: the optional
client access-token route is off, while server components and route handlers
obtain tokens from the managed session. Next.js route handlers provide the BFF
surface, and its proxy supplies the nonce CSP request/response headers.

No user profile claim grants a merchant role. FastAPI resolves the immutable
OIDC identity against the current PostgreSQL membership on each request.
Membership and identity revocation therefore continue to take effect on the
next BFF request.

## Verification contract

- incomplete, malformed, non-HTTPS production configuration fails closed;
- development HTTP works only on loopback hosts;
- mutation origins must exactly equal the configured application origin;
- browser code has no access-token endpoint or tenant selector;
- internal database identifiers and record versions are removed from client
  inventory data;
- inventory read and import preview BFF routes are present in the production
  build;
- the preview UI never claims that inventory was applied;
- frontend tests, strict typechecking, dependency audit, production build, and
  build verification pass;
- the existing backend authorization, RLS, upload, and security suites remain
  green.

## Remaining deployment gates

- Provision and configure the Product Owner's Auth0 tenant/application/API,
  callback/logout URLs, MFA policy, and production secrets.
- Run real-browser valid login, invalid callback/state, logout, back-channel
  revocation, expired session, removed membership, role change, multiple-tab,
  CSRF, XSS, CSP, and direct API tests against staging.
- Configure the edge/reverse proxy to reject oversized request bodies and rate
  limit login and preview routes before multipart parsing.
- Select and validate the malware scanner required by Decision 0007; the
  FastAPI preview continues to return `503` without it.
- Replace the single server-configured workspace with a server-persisted,
  membership-validated workspace switcher when the second workspace is in
  scope.
- Review stateful/shared session storage before horizontal scaling. This
  checkpoint uses the SDK's encrypted stateless session cookie.

## Next checkpoint

After Product Owner review, configure a staging Auth0 application and exercise
the real browser/security matrix. Do not enable real merchant upload or
inventory apply until the malware-scanner, edge-limit, and apply-workflow gates
are separately accepted.

# Decision 0008: Phase 1 Merchant Inventory UX

Date: 2026-10-09

## Status

Ready for Product Owner review.

## Implemented boundary

- The commercial interface starts in `apps/web` as a separate Next.js 16 and
  TypeScript application. The root Streamlit application remains the fictional
  evaluation demo.
- `/inventory` uses merchant language: Product, Variant, SKU, Location, In
  stock, Low-stock level, Status, and Last updated. Internal product, variant,
  location, and balance UUIDs are absent from the normal table.
- Search covers product, variant, SKU, location name, and location code. The
  attention filter and summary counts use deterministic code, including a
  distinct out-of-stock state.
- The screen always labels the source as a manual CSV snapshot and tells the
  merchant to inspect freshness before acting.
- The CSV workflow shows its three bounded steps, provides the reviewed UTF-8
  template, states the 5 MB/10,000-row limits, and says that preview changes no
  stock.
- Import controls require the server-provided `inventory.import` permission.
  Hidden/disabled controls remain a convenience; FastAPI continues to enforce
  the permission on every request.
- `GET /api/v1/workspace` now returns the current role's permission names so
  the UI does not duplicate role grants. It contains no secrets or target
  record identifiers.
- The current page fails closed with a clear session-configuration state. It
  neither reads bearer tokens from browser storage nor invents a local login.
- Basic response hardening removes the framework header and sets nosniff,
  frame-deny, referrer, and restrictive browser capability headers. A reviewed
  nonce-based CSP remains a deployment gate.
- Next.js, React, TypeScript, and type packages are exact-version locked.
  Frontend unit tests, strict typechecking, dependency audit, and production
  build run in the local security gate and GitHub Actions.

## Deliberately unavailable

- managed browser login/session and a server-side BFF/token adapter;
- a live API fetch from the merchant page;
- file selection/upload while the secure session adapter is absent;
- inventory adjustment, bulk edit, import apply, and any model-driven write;
- Reserved and Available quantities, because no order reservation source has
  been selected or modeled.

Displaying zeros in the disconnected state represents zero loaded UI rows, not
a claim that the merchant has no stock.

## Security review

This creates a new browser surface and dependency tree. The browser never gets
database credentials, provider secrets, or a stored long-lived bearer token.
The page accepts no upload in its current fail-closed configuration. API role
checks and PostgreSQL tenant RLS remain authoritative.

Before enabling live merchant data, complete and test:

- managed OIDC login with HTTP-only, Secure, SameSite cookies;
- exact callback/origin/host configuration, CSRF protection, session rotation,
  logout/revocation, MFA policy, and recent reauthentication where required;
- server-side workspace selection and API token forwarding that cannot accept
  tenant authority from an untrusted browser field;
- nonce-based CSP and production edge/request limits;
- browser tests for XSS, CSRF, role changes, tenant switching, stale sessions,
  direct API calls, and inaccessible controls.

## Verification contract

- production Next.js build and strict TypeScript checks pass;
- status, summary, filter, and permission helpers pass deterministic tests;
- the downloadable template exactly matches the reviewed source template;
- the rendered route contains no fictional merchant inventory;
- disconnected configuration keeps import disabled;
- workspace permissions come from the backend policy map;
- the existing backend authorization, RLS, upload, and security suites remain
  green.

## Next checkpoint

Select and implement the managed browser-session/BFF boundary, then connect the
inventory read and preview APIs without exposing bearer tokens to browser
storage. Keep apply/write disabled.

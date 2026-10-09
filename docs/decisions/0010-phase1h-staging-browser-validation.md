# Decision 0010: Phase 1H Staging Browser Validation

Date: 2026-10-09

## Status

In progress; external staging configuration is required.

## Implemented test boundary

- Pinned Playwright tests run against installed Microsoft Edge locally and
  pinned Chromium in CI.
- The signed-out suite verifies fail-closed inventory, browser security
  headers, token absence, disabled client access-token route and cross-origin
  mutation rejection.
- A structural staging preflight checks 14 required settings without printing
  their values.
- Authenticated tests consume only a local ignored browser-state file created
  after the Product Owner manually completes Auth0 login.
- The browser-state file, test artifacts and reports are excluded from Git.
- The full manual validation matrix is recorded in
  `docs/PHASE_1H_BROWSER_VALIDATION.md`.

## Current evidence

- Nine frontend unit tests and strict TypeScript checks pass.
- Five signed-out Microsoft Edge browser-security tests pass locally.
- The BUILD security gate passes: secret scan, Ruff, Bandit, Python and npm
  dependency audits, 129 deterministic tests, the short load check, frontend
  tests, production browser tests and build verification all pass. Eleven
  PostgreSQL integration tests remain skipped locally when Docker is absent.
- Auth0 staging application/API, OIDC settings, the Supabase staging schema,
  restricted runtime/authenticator logins and a synthetic merchant workspace
  are configured. The temporary migration credential was removed after use.
- Preflight now fails closed only because the HTTPS frontend and API deployment
  origins have not been assigned.

## Remaining gate

Deploy the HTTPS app/API services, configure one staging Auth0 identity and its
merchant membership, then capture a manually authenticated staging session.
Run the authenticated suite and complete the manual security matrix. Phase 1H
is not accepted until those results are reviewed by the Product Owner.

The unauthenticated browser suite runs against a production Next.js build so
development-only CSP allowances cannot satisfy the security gate.

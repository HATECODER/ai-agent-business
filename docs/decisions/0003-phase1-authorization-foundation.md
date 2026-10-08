# Decision 0003: Phase 1 Authorization Foundation

Date: 2026-10-08

## Status

Accepted by the Project Owner on 2026-10-08.

## Implemented boundary

The commercial product now has a separate `backend` package. The existing
Streamlit/SQLite application remains the fictional evaluation pilot.

This checkpoint implements:

- a minimal FastAPI application with a non-sensitive liveness endpoint;
- the six fixed R1 merchant roles;
- deny-by-default merchant permissions and `all`, `domain`, and `own` scopes;
- explicit active-tenant authority resolved only from an exact active
  server-side membership;
- fail-closed handling for missing, duplicate, suspended, revoked, and invalid
  memberships;
- object tenant checks that return a non-enumerating `Resource not found`
  response for cross-tenant access;
- separate platform roles, permissions, and authority type so platform staff
  do not inherit merchant authority;
- focused role, revoked-membership, own-record, and two-tenant adversarial
  tests;
- Bandit coverage for the new backend in both the local gate and CI.

## Deliberately deferred

The liveness endpoint is the only HTTP endpoint. This checkpoint does not add
temporary header authentication, accept tenant authority from the browser, or
reuse the pilot owner allowlist as a commercial membership system.

Managed OIDC validation, persistent memberships, PostgreSQL migrations,
restricted runtime roles, Row-Level Security, audit persistence, and protected
business endpoints belong to the following Phase 1 checkpoints.

## Verification

- 12 focused backend tests passed;
- 87 full deterministic tests passed;
- Ruff and Bandit passed;
- secret and repository policy checks passed;
- dependency audit reported no known vulnerability;
- short load check completed with zero errors.

The test client currently reports one upstream Starlette/AnyIO deprecation
warning. It does not affect behavior, but dependency updates should remove it
before the production release gate.

## Next checkpoint

Add PostgreSQL and Alembic foundations for tenants, identities, memberships,
locations, and audit events. Apply tenant-scoped keys and default-deny RLS,
then prove isolation through database integration tests using two tenants and
a restricted runtime role.

# Decision 0004: Phase 1 PostgreSQL and RLS Foundation

Date: 2026-10-08

## Status

Accepted by the Product Owner on 2026-10-08.

## Implemented boundary

- Alembic owns the commercial PostgreSQL schema history.
- External OIDC identity (`issuer`, `subject`) is separate from the internal
  identity UUID used by foreign keys and database policy.
- Tenant membership stores the fixed R1 role, state, and permission version.
- Tenant-owned location and audit records carry a required `tenant_id`.
- Platform staff is stored separately from merchant memberships.
- The application sets tenant, identity, membership, and permission version as
  transaction-local PostgreSQL settings using parameterized statements.
- The fixed `bizpilot_runtime` role is non-superuser, cannot create roles or
  databases, does not inherit privileges, and has no `BYPASSRLS`.
- RLS checks an exact active membership and active tenant. Cross-tenant reads
  return no row, and cross-tenant writes fail.
- Location and audit tables use `FORCE ROW LEVEL SECURITY`. Tenant and
  membership roots remain owner-readable only so the hardened membership
  predicate can perform authorization bootstrap; the runtime role is never
  their owner.
- The platform-staff table has no merchant-runtime grant.

## Security constraints

`roles.sql` is intended for a dedicated BizPilot database. It contains no
password. Deployment creates a separate login credential in the secret manager
and grants it permission to assume only `bizpilot_runtime`.

Migration credentials are separate from runtime credentials. The runtime role
cannot run migrations, own tables, read platform staff, or bypass row policy.

## Verification contract

- offline migration SQL contains all required tables, policies, grants, and
  forced RLS controls;
- unit tests verify PostgreSQL-only configuration and transaction-local,
  parameterized context;
- disposable PostgreSQL integration tests apply and roll back the migration;
- two tenants with overlapping access patterns cannot read or insert each
  other's locations;
- stale permission versions and revoked memberships lose access;
- the merchant runtime cannot read platform staff.

## Verification evidence

On 2026-10-08, the migration was applied to a disposable PostgreSQL 17.6
container using the pinned official image digest. All five database integration
tests passed, including migration rollback. The full security gate completed
with 97 tests passed, zero load-check errors, and no known dependency
vulnerability. The container was removed after the test.

GitHub Actions run
[`37764800681`](https://github.com/HATECODER/ai-agent-business/actions/runs/37764800681)
then passed the Windows test and security job, the PostgreSQL RLS integration
job, and the dependent Linux Docker build. A concurrent-confirmation race found
by the first hosted run was reproduced locally and fixed in commit `457e884`;
the exact hosted load check and 20 repeated local runs then passed.

## Deferred

- managed OIDC JWT validation and identity synchronization;
- production login/secret-manager provisioning;
- products, variants, inventory balances, movements, tasks, and imports;
- support-access grants and platform console endpoints;
- backup/restore exercise in the target managed PostgreSQL service.

## Next checkpoint

Implement managed OIDC token validation, persistent identity/membership lookup,
active-tenant resolution, protected FastAPI dependencies, sanitized denial
telemetry, and session/membership revocation tests.

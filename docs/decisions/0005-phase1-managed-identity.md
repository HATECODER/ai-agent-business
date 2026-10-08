# Decision 0005: Phase 1 Managed Identity and Tenant Authority

Date: 2026-10-08

## Status

Accepted by the Product Owner on 2026-10-08.

## Implemented boundary

- The commercial API validates managed OIDC access tokens with PyJWT and JWKS.
- Verification fixes the accepted algorithm to `RS256` and requires a valid
  signature, exact issuer and audience, subject, issued-at time, and expiry.
- OIDC issuer and JWKS configuration must use bounded HTTPS URLs. Tokens and
  subjects are never written to authorization-denial telemetry.
- `X-BizPilot-Tenant` is only an active-workspace selector. It grants no
  authority by itself.
- A separate `bizpilot_authenticator` PostgreSQL role can execute one narrowly
  scoped SECURITY DEFINER membership resolver and has no table privileges.
- The resolver combines the verified issuer/subject with the selected tenant
  and returns authority only for an active identity, tenant, and membership.
- Identity `status` and `tokens_valid_after` support local suspension,
  revocation, and invalidation of already-issued tokens.
- Every protected request performs a fresh persistent membership lookup. Role,
  membership state, tenant state, and permission version are not trusted from
  browser input or JWT custom claims.
- The protected `GET /api/v1/workspace` endpoint returns only the current
  workspace ID, role, and permission version.
- API failures use generic 400/401/403/503 responses. Security telemetry records
  only a bounded denial category and a server-generated correlation ID.

## Security constraints

The API runtime needs two separately provisioned database login credentials:
one permitted to assume `bizpilot_authenticator`, and one permitted to assume
`bizpilot_runtime`. Neither credential owns tables, runs migrations, or has
`BYPASSRLS`. Both remain server-side secret-manager values.

The identity provider remains responsible for login, MFA, recovery, and its own
session lifecycle. BizPilot's database check is an additional authorization and
revocation boundary; it does not replace provider-side token revocation.

## Verification contract

- wrong signature, algorithm, issuer, audience, expiry, subject, and token age
  fail closed;
- missing credentials and workspace selection cannot reach a protected route;
- another tenant's selector yields no authority;
- membership and identity revocation are effective on the next API request;
- a token issued before `tokens_valid_after` yields no authority;
- the authenticator uses parameterized input and has no direct table grants;
- logs and API responses contain no bearer token, subject, database detail, or
  provider error payload;
- the real PostgreSQL suite applies and rolls back both migrations.

## Current limitations

- No production identity project, JWKS endpoint, database login, or secret
  manager has been provisioned in this repository.
- Browser login/callback/cookie/CSRF flows and MFA policy remain deployment and
  later feature gates. This API currently accepts bearer access tokens.
- Platform staff authentication uses a separate future route/audience and is
  not implemented by this merchant dependency.
- The workspace session endpoint proves the boundary; commercial product,
  inventory, import, and task endpoints remain deferred.

## Verification evidence

On 2026-10-08, the full local BUILD security gate passed with 111 tests and six
expected PostgreSQL skips, zero load-check errors, and no known locked-dependency
vulnerability. The six-test real PostgreSQL 17.6 suite then passed against the
pinned official image. It applied and rolled back both migrations and verified
authenticator privileges, cross-tenant denial, identity cutoff/revocation, and
membership revocation. The disposable database container was removed.

## Next checkpoint

Extend tenant-owned product, variant, location, inventory-balance, and movement
schemas behind RLS. Then expose read-only inventory APIs using the Phase 1C
dependency before enabling staged CSV upload or any merchant write.

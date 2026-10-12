# November demo Day 12 result

Date: 2026-10-12
Status: implemented locally; awaiting Product Owner approval

## Changed boundaries tested

- Copilot requests require a bearer token and workspace selector.
- The active membership is resolved before Copilot execution.
- `copilot.use` is checked at the endpoint, and each deterministic reader keeps
  its existing domain permission check.
- The browser BFF retains exact same-origin validation, server-side Auth0
  session use and the 500-character input limit.
- No bearer token is created or exposed by the browser component.

## Controlled failure results

| Failure | Public result |
|---|---|
| Missing authentication | `401 Authentication required` |
| Missing workspace selector | `400 Select a workspace` |
| Domain permission denied | `403 Permission denied for this question` |
| Unsupported question | `422` with fixed supported-question guidance |
| Database/source unavailable or invalid | `503 Source facts unavailable` |
| Prompt over 500 characters | `422` validation response |
| External model key/provider unavailable | Deterministic mode remains available; no provider is called |

Private tokens, prompts, membership details, database details and parser errors
were injected into failure tests and did not appear in security logs or public
responses. Logs retain only the denial category and generated correlation ID.

## Existing evidence reused

- PostgreSQL cross-tenant/RLS isolation from Day 8 and Phase 1H.
- Auth0 membership revocation and Redis session invalidation from Phase 1H.
- CSV preview denial/scanner/parser tests from Days 4-6.

Those unchanged boundaries were not manually reconfigured or repeatedly tested
through a new browser login.

## Verification

- Focused backend tests cover authentication, request bounds, domain denial,
  unsupported input, source failures and log redaction.
- Frontend tests verify BFF origin/session/bounds wiring and safe React rendering.
- Full repository, production build and static checks are recorded after the
  final Day 12 verification run.

## Remaining

Day 13 will prepare a deployable candidate, record its commit SHA, run CI and
write backup/restore plus rollback instructions. Deployment and push remain
subject to the existing explicit approval workflow.

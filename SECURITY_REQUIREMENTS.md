# BizPilot AI Security Requirements and Push Gate

**Owner:** Engineering and Product Owner
**Initial version:** 2026-10-08
**Applies to:** source code, configuration, infrastructure, AI tools, data connectors, releases, and support operations

## 1. Purpose

This document is the security contract for BizPilot development. It is designed to reduce likely attacks and data leaks without turning early product development into a compliance exercise.

Security is added in layers:

| Stage | What is allowed | Security posture |
|---|---|---|
| **BUILD** | Local development, CI, fictional/synthetic data | Fast baseline checks on every push |
| **PILOT** | Named evaluators or merchants, limited features, controlled data | Identity, authorization, audit, recovery, and enabled-feature tests |
| **PRODUCTION** | Real multi-tenant customer use | Tenant isolation, hardened deployment, monitoring, incident response, and independent testing |
| **HIGH_RISK** | Payments, refunds, publishing, purchasing, HR, bulk messaging, sensitive exports | Separate threat review, stronger approval, domain controls, and feature-specific release gate |

Future-stage requirements do not block ordinary BUILD work. A requirement becomes blocking when its stage is reached or when its related feature is enabled.

This follows the risk-driven, iterative approach described by [OWASP SAMM](https://owasp.org/projects/samm) and the secure-development practices in [NIST SSDF SP 800-218](https://csrc.nist.gov/pubs/sp/800/218/final). [OWASP ASVS 5.0](https://owasp.org/projects/asvs) is the technical verification reference for the commercial web application; this document does not claim certification.

## 2. Gate rules

### 2.1 Blocking policy

Block a push or release when any of these applies to an enabled path:

- a real secret is present in code, configuration, history, build output, or logs;
- deterministic tests, authorization tests, secret scan, static scan, dependency audit, or build fail;
- a known reachable critical/high vulnerability has no reviewed mitigation;
- authentication or authorization fails open;
- another tenant/user can read or change an unauthorized object;
- a sensitive action can execute without the required current permission and approval;
- production startup can seed demo data or silently use an unsafe fallback;
- migration, backup, or rollback risk can cause unrecoverable customer-data loss;
- required security evidence is missing for the stage being released.

Do not block BUILD work only because a future feature has not been implemented. Mark it `NOT_APPLICABLE_YET` and keep the feature disabled.

### 2.2 Exception process

A temporary exception is allowed only for a noncritical control when all fields are recorded:

- requirement ID and reason;
- affected environment/feature;
- risk owner;
- compensating control;
- expiry date no longer than 30 days;
- tracking issue and removal test.

Exceptions are not permitted for exposed secrets, known cross-tenant access, authentication bypass, unauthorized external actions, or reachable unmitigated critical vulnerabilities.

## 3. Every-push BUILD requirements

These requirements are mandatory now and run without live model calls or production credentials.

| ID | Requirement | Verification | Current state |
|---|---|---|---|
| `SEC-BLD-001` | No `.env`, deployed secret file, private key, SQLite data, backup, or release credential is tracked. | Repository policy checker and `.gitignore` review | Enforced |
| `SEC-BLD-002` | Common Gemini/OpenAI key shapes are scanned in tracked/new files and Git patches without printing values. | `scripts/check_secrets.py` | Enforced |
| `SEC-BLD-003` | Runtime and development dependencies are version locked for repeatable builds. | Lock files and CI install | Enforced |
| `SEC-BLD-004` | Syntax errors and undefined Python names fail CI. | Ruff `E9,F` | Enforced |
| `SEC-BLD-005` | Common Python security issues fail the static scan. | Bandit | Enforced |
| `SEC-BLD-006` | Known dependency vulnerabilities fail the dependency audit. | `pip-audit` | Enforced; findings require reachability triage |
| `SEC-BLD-007` | Deterministic tests run offline and do not require live credentials. | pytest | Enforced |
| `SEC-BLD-008` | The container image builds from committed files. | Linux Docker build in CI | Enforced |
| `SEC-BLD-009` | CI token permissions remain minimal. | `contents: read`; no write permission by default | Enforced |
| `SEC-BLD-010` | Production secrets are not supplied to pull-request test jobs. | Workflow/repository settings review | Required repository setting |
| `SEC-BLD-011` | Writes use validated backend functions and parameterized database queries. | Review, Bandit, domain tests | Enforced for current paths |
| `SEC-BLD-012` | Finance and inventory facts are calculated by deterministic code, not the model. | Domain and agent tests | Enforced |
| `SEC-BLD-013` | High-risk operations remain absent or disabled until their feature gate passes. | Allowlist review and negative tests | Enforced for current prototype |
| `SEC-BLD-014` | User-visible errors do not expose provider payloads, tokens, stack traces, or database details. | Error-path tests and review | Enforced for current paths |
| `SEC-BLD-015` | AI calls have input/output/tool/call/time/cost bounds. | Run-policy tests | Enforced |
| `SEC-BLD-016` | Internal writes use proposal, exact-payload confirmation, execution-time authorization, audit, and idempotency. | Action tests | Enforced |
| `SEC-BLD-017` | Security-relevant changes include or update misuse/negative tests. | Change checklist | Manual gate |
| `SEC-BLD-018` | New dependency, external action, endpoint, upload path, or secret receives explicit security review. | Change checklist | Manual gate |

## 4. Authentication and session requirements

| ID | Stage | Requirement |
|---|---|---|
| `SEC-ID-001` | PILOT | Use a managed identity provider; never build password storage or password reset locally. |
| `SEC-ID-002` | PILOT | Validate token signature, issuer, audience, expiry, and exact redirect/callback configuration. |
| `SEC-ID-003` | PILOT | Authentication alone grants no business access; require an active server-side membership/allowlist. |
| `SEC-ID-004` | PILOT | Recheck authorization for every protected read, proposal, approval, and execution. |
| `SEC-ID-005` | PRODUCTION | Require MFA for Platform Admins and Merchant Owners; offer MFA to all merchant users. |
| `SEC-ID-006` | PRODUCTION | Require recent reauthentication for ownership transfer, member/role changes, connector-secret changes, sensitive exports, and high-risk actions. |
| `SEC-ID-007` | PRODUCTION | Use secure, HTTP-only, SameSite cookies, CSRF protection for cookie-authenticated mutations, and session rotation/revocation. |
| `SEC-ID-008` | PRODUCTION | Rate-limit login, recovery, invitation, token, and verification flows without enabling account enumeration. |
| `SEC-ID-009` | PRODUCTION | A removed/suspended user promptly loses API, background job, approval, export, and active-session access. |
| `SEC-ID-010` | PRODUCTION | Ownership transfer prevents zero-owner state and requires a logged, strongly authenticated workflow. |

References: [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html) and [OWASP MFA Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Multifactor_Authentication_Cheat_Sheet.html).

## 5. Authorization and tenant isolation

| ID | Stage | Requirement |
|---|---|---|
| `SEC-TEN-001` | PRODUCTION | Every tenant-owned record has a required `tenant_id` and tenant-scoped relationships/constraints. |
| `SEC-TEN-002` | PRODUCTION | Tenant comes from verified identity/membership or verified connector mapping, never from an untrusted record ID/header alone. |
| `SEC-TEN-003` | PRODUCTION | Every ID-based endpoint verifies tenant, actor, permission, object ownership, and allowed fields. UUIDs do not replace authorization. |
| `SEC-TEN-004` | PRODUCTION | PostgreSQL RLS uses default-deny policies; runtime users are not table owners and do not have `BYPASSRLS`. Use `FORCE ROW LEVEL SECURITY` where appropriate. |
| `SEC-TEN-005` | PRODUCTION | API, worker, cache, object, export, search/RAG, analytics, and audit paths all preserve tenant scope. |
| `SEC-TEN-006` | PRODUCTION | Cache keys include tenant, actor/audience, permission/config version, and source version where relevant. |
| `SEC-TEN-007` | PRODUCTION | Jobs carry validated tenant/actor authority; payload data cannot grant itself permission. |
| `SEC-TEN-008` | PRODUCTION | Two-tenant tests attack every data path and return zero unauthorized results/effects. |
| `SEC-TEN-009` | PRODUCTION | Platform Admin and merchant identity use distinct roles, routes, audiences, and policies. |
| `SEC-TEN-010` | PRODUCTION | Support sees redacted metadata by default. Data access is scoped, approved, expiring, visible, and audited. |

References: [OWASP object-level authorization](https://api-security.owasp.org/editions/2023/en/0xa1-broken-object-level-authorization/) and [PostgreSQL row security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html).

## 6. Input, API, browser, and file security

| ID | Stage | Requirement |
|---|---|---|
| `SEC-INP-001` | BUILD | Validate request/tool/domain input with explicit schemas, bounds, and allowlists; reject unknown sensitive fields. |
| `SEC-INP-002` | BUILD | Use parameterized SQL and safe subprocess argument lists; never concatenate untrusted input into SQL, shell, template, or paths. |
| `SEC-INP-003` | PRODUCTION | Encode untrusted output for HTML/URL/JSON context and configure CSP plus reviewed security headers. |
| `SEC-INP-004` | PRODUCTION | Configure exact origins, host validation, HTTPS redirects, request/body limits, timeouts, and endpoint rate limits. |
| `SEC-INP-005` | FEATURE:UPLOAD | Allowlisted extension/MIME, random storage name, path confinement, file/row/decompression limits, quarantine, and malware scan. |
| `SEC-INP-006` | FEATURE:UPLOAD | Never execute macros/formulas. Protect spreadsheet exports from formula injection. |
| `SEC-INP-007` | FEATURE:UPLOAD | Tenant-scope upload, preview, job, error file, signed download, retention, and deletion. |
| `SEC-INP-008` | FEATURE:WEBHOOK | Verify signature on the raw body, deduplicate delivery IDs, tolerate retries/out-of-order events, and reject invalid replays. |
| `SEC-INP-009` | FEATURE:CONNECTOR | Use minimum scopes, encrypt tokens, isolate by tenant/environment, rotate/revoke, and never expose tokens to browser/model. |
| `SEC-INP-010` | FEATURE:EXPORT | Permission check, bounds, background generation, short-lived download, audit, and notification for sensitive exports. |

## 7. Data protection, privacy, and logging

| ID | Stage | Requirement |
|---|---|---|
| `SEC-DAT-001` | PILOT | Store and send only fields required for the enabled use case. Synthetic data is default before real-data approval. |
| `SEC-DAT-002` | PRODUCTION | Maintain a data inventory: purpose, owner, sensitivity, region, processor, retention, export, and deletion. |
| `SEC-DAT-003` | PRODUCTION | TLS protects transit and managed encryption protects databases, backups, objects, and secrets at rest. |
| `SEC-DAT-004` | BUILD | Logs/errors exclude keys, credentials, tokens, connection strings, and raw provider errors. |
| `SEC-DAT-005` | PRODUCTION | Default telemetry excludes customer message bodies and sensitive business/personal fields. |
| `SEC-DAT-006` | PRODUCTION | Audit records actor, tenant, authority, action, target, outcome, source/version, and time; modification/export is restricted. |
| `SEC-DAT-007` | PRODUCTION | Retention, deletion, legal hold, backup expiry, and accounting/audit retention are documented separately. |
| `SEC-DAT-008` | PRODUCTION | Export/deletion reaches DB, objects, search/vector index, cache, queued work, and connector mappings. |
| `SEC-DAT-009` | PRODUCTION | Backups use separate protected credentials and restore into an isolated environment for verification. |
| `SEC-DAT-010` | PRODUCTION | Database and object backups are both covered; RPO/RTO claims require measured evidence. |

Reference: [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html).

## 8. Secrets and cryptographic material

| ID | Stage | Requirement |
|---|---|---|
| `SEC-SEC-001` | BUILD | Secrets never enter Git, `.env.example`, screenshots, issues, fixtures, model prompts, or normal logs. |
| `SEC-SEC-002` | PILOT | Deployed secrets come from the hosting secret manager and are separated for demo, staging, and production. |
| `SEC-SEC-003` | PRODUCTION | Each secret has owner, purpose, scope, environment, rotation, revocation, and incident contact. |
| `SEC-SEC-004` | PRODUCTION | Connector/model/database credentials use least privilege and tenant-specific credentials where supported. |
| `SEC-SEC-005` | PRODUCTION | CI deployment uses short-lived identity/OIDC where supported or a narrowly scoped protected token. |
| `SEC-SEC-006` | PRODUCTION | Rotation supports overlap where needed and is rehearsed without exposing values. |

Reference: [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html).

## 9. AI and agent security

| ID | Stage | Requirement |
|---|---|---|
| `SEC-AI-001` | BUILD | Prompts are guidance, never authorization. Backend policy chooses tools and rechecks every invocation. |
| `SEC-AI-002` | BUILD | The model never receives database credentials, secrets, unrestricted tools, or arbitrary code/shell execution. |
| `SEC-AI-003` | BUILD | Deterministic code owns money, inventory, dates, permissions, transitions, and idempotency. |
| `SEC-AI-004` | BUILD | Model/tool input and output have length, call-count, timeout, token, result-size, and cost limits. |
| `SEC-AI-005` | PILOT | Unsupported/sensitive actions are refused before a model call where possible; errors are sanitized and do not silently enable fallback. |
| `SEC-AI-006` | PRODUCTION | Model context is minimum necessary and tenant/role scoped. Retrieved/uploaded/connector text is untrusted. |
| `SEC-AI-007` | PRODUCTION | External/destructive action requires validated exact proposal, current permission, expiry/revocation check, idempotency, and audit. |
| `SEC-AI-008` | PRODUCTION | Fallback provider is disabled unless tenant data-processing and budget policy permit it. |
| `SEC-AI-009` | FEATURE:RAG | Retrieval enforces tenant/document/chunk ACL/version; revoked/deleted content is removed. |
| `SEC-AI-010` | HIGH_RISK | Payments, refunds, procurement, publishing, bulk messaging, price/ad-budget changes, and HR decisions need separate threat review. |

## 10. Business actions and data integrity

| ID | Stage | Requirement |
|---|---|---|
| `SEC-ACT-001` | BUILD | Every write has validated input, transaction boundaries, clear result, and safe error behavior. |
| `SEC-ACT-002` | BUILD | Retryable workflows use logical idempotency and database uniqueness where appropriate. |
| `SEC-ACT-003` | PRODUCTION | Approval binds actor, tenant, action, normalized payload/hash, source/config version, expiry, and authority. |
| `SEC-ACT-004` | PRODUCTION | Unknown external outcome is reconciled before retry; timeout is not assumed failure. |
| `SEC-ACT-005` | FEATURE:INVENTORY | Stock change records actor, reason, source, location, before/after, and idempotency; correction uses reversal. |
| `SEC-ACT-006` | FEATURE:IMPORT | Import has staging, validation, preview, conflict/version check, explicit apply, progress, error report, and audit. |
| `SEC-ACT-007` | FEATURE:FINANCE | Financial definitions are documented/reconciled; money uses minor units/currency and not model arithmetic. |
| `SEC-ACT-008` | HIGH_RISK | Separate initiation/approval where practical; reauthenticate and show recipient/amount/scope before execution. |

## 11. Dependency, build, and deployment security

| ID | Stage | Requirement |
|---|---|---|
| `SEC-SUP-001` | BUILD | Dependencies are minimized, locked, audited, and updated through reviewed changes. |
| `SEC-SUP-002` | BUILD | CI actions use trusted publishers and supported major versions; production maturity pins critical actions/images by digest/commit. |
| `SEC-SUP-003` | BUILD | CI jobs use minimal permissions and no unnecessary secrets; untrusted PRs cannot access production credentials. |
| `SEC-SUP-004` | PRODUCTION | Produce SBOM and scan artifacts; retain digest and scan evidence with release. |
| `SEC-SUP-005` | PRODUCTION | Promote the same tested immutable artifact from staging to production. |
| `SEC-SUP-006` | PRODUCTION | Migrations use a dedicated role, lock, compatibility plan, backup, verification, and rollback/forward-fix plan. |
| `SEC-SUP-007` | PRODUCTION | Runtime uses nonroot/minimal images, resource limits, minimal filesystem permissions, and separate service identities. |
| `SEC-SUP-008` | PRODUCTION | Deployment requires HTTPS, exact origins/hosts, private DB/broker, readiness checks, and no demo seed hook. |

Reference: [GitHub supply-chain security guidance](https://docs.github.com/en/code-security/tutorials/implement-supply-chain-best-practices/end-to-end-supply-chain-overview).

## 12. Availability, monitoring, and incident response

| ID | Stage | Requirement |
|---|---|---|
| `SEC-OPS-001` | PILOT | Provider outage leaves deterministic dashboards available and does not trigger unbounded retries. |
| `SEC-OPS-002` | PRODUCTION | Rate, concurrency, queue, import, file, result, and budget limits prevent one tenant from exhausting resources. |
| `SEC-OPS-003` | PRODUCTION | Alert on auth anomalies, authorization failures, webhook signature failures, sync lag, backlog, provider errors, cost spikes, and backup failure. |
| `SEC-OPS-004` | PRODUCTION | Correlation IDs join request, tenant, actor, job, tool, provider, and audit without sensitive payloads. |
| `SEC-OPS-005` | PRODUCTION | Runbooks cover secret exposure, takeover, tenant leak, malicious upload, corruption, connector compromise, abuse, and denial of service. |
| `SEC-OPS-006` | PRODUCTION | Security contacts, severity, containment, evidence, recovery, communications decision, and post-incident review are assigned. |
| `SEC-OPS-007` | PRODUCTION | Restore, rotation, revocation, rollback, and tenant-disable exercises are performed and timed. |
| `SEC-OPS-008` | PRODUCTION | Security patches have risk-based response targets and an emergency release procedure. |

## 13. Feature activation checklist

Before enabling a new feature, answer:

1. What new data, identity, secret, endpoint, file, model context, or side effect is introduced?
2. Which tenant/role can access it, and where is that enforced server-side?
3. What abuse, cost abuse, replay, concurrency, and failure-after-commit cases exist?
4. What is the source of truth and freshness/conflict policy?
5. Which data reaches a model, log, analytics tool, support user, or subprocessor?
6. What tests prove authorization, isolation, validation, idempotency, redaction, and failure behavior?
7. How is it disabled, rolled back, reconciled, and recovered?
8. Which requirements change from `NOT_APPLICABLE_YET` to blocking?

Answers can be short for low-risk changes. Authentication, tenant scope, uploads, connectors, exports, external actions, finance, HR, and deletion require a written threat-model update.

## 14. Push and release procedure

### Before every push

Run:

```powershell
.\scripts\security_gate.ps1
```

It runs the policy checker, secret scan, Ruff, Bandit, dependency audit, deterministic tests, and a short load check without live AI calls. Docker build remains in GitHub Actions because local Docker may be unavailable.

Review `.github/pull_request_template.md` for the changed feature. Documentation-only changes may mark code-specific items not applicable.

### On every GitHub push/pull request

GitHub Actions repeats the automated checks and builds the Linux container. Branch protection should require the `test` and `docker` jobs before merge when repository settings permit it.

### Before PILOT or PRODUCTION promotion

Record commit/artifact digest, enabled features/stage, gate results, identity/tenant tests, vulnerability triage, restore/rollback evidence, limitations/exceptions, approver, and release decision.

## 15. Current truthful status

### Implemented for the restricted synthetic pilot

- secret/database ignore rules and redacted secret scan;
- locked dependencies, dependency audit, Ruff, Bandit, pytest, load check, and Linux Docker CI build;
- OIDC-capable pilot auth and owner allowlist;
- execution-time authorization for protected operations;
- validated proposals, exact confirmation, idempotency, and audit for current internal actions;
- bounded AI calls, sanitized failures, and deterministic inventory/finance;
- backup/restore tooling and release evidence.

### Not yet implemented; related production feature must remain disabled

- commercial multi-tenant memberships/roles and PostgreSQL RLS;
- production Platform Admin/support console;
- upload/import quarantine and malware scanning;
- connector/webhook ingestion and reconciliation;
- private object storage and tenant-scoped exports;
- production MFA/session/re-authentication flows;
- RAG ACL/version deletion;
- DAST, SBOM/artifact attestation, and independent penetration test;
- real merchant retention/deletion and production incident operation.

Passing the BUILD gate means the change meets the current development baseline. It does not mean the product is secure enough for real multi-tenant customer data.

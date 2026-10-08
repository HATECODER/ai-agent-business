# BizPilot: 2–3 Day Delivery Checklist

Date: **2026-10-04**; implementation evidence updated through **2026-10-08**. Parent specification: [PRODUCTION_PLAN.md](PRODUCTION_PLAN.md), especially section 0. Status: **Day 3 local engineering gates complete; hosted deployment, live-provider and real-browser validation pending**.

## Deliverable and limits

Deliver a restricted owner evaluation pilot over fictional data: authenticated access, accurate metric labels, bounded AI usage, optional confirmed internal drafts, visible evidence, tested deployment and recovery. Retain the existing Python/Streamlit/SQLite stack for this sprint. This is not the customer-facing commerce V0, a shared multi-tenant SaaS, or all 18 production capabilities.

Default: synthetic data only; no uploads, customer messaging, payment actions, external publishing, real source connection, RAG, fine-tuning, HR or new agent profiles. No real records may be introduced merely because login works. The full data/privacy/tenant release gates remain in the production plan.

## Capacity and critical path

Assume two experienced engineers, A (application/domain) and B (platform/AI/testing), each available 8 hours/day. Work estimates include feature-specific tests and review. Total **42 hours planned + 6 hours contingency = 48 person-hours**. These are estimates, not delivery guarantees. Product owner contributes scope decisions and acceptance; infrastructure accounts must already be available.

| Day | Engineer A | Engineer B | Gate |
|---|---|---|---|
| 1 | D1-1 1h; D1-3 3h; D1-4 3h; buffer 1h | D1-2 5h; D1-5 2h; buffer 1h | Data mode, auth and semantics tests pass |
| 2 | D2-2 4h; D2-4 3h; buffer 1h | D2-1 4h; D2-3 3h; buffer 1h | All enabled actions and AI failures are bounded and tested |
| 3 | D3-1 4h; D3-3 3h; buffer 1h | D3-2 4h; D3-4 3h; buffer 1h | Release evidence reviewed; deploy or explicitly no-go |

Critical path: scope → auth/data-mode decisions → shared policy boundary → agent integration → integrated tests → staging → deployed auth/restore/model smoke → release review. Agree wrapper interfaces on day 1 so A/B can work independently. Day 3 testing follows integration; deployment preparation can proceed while A runs deterministic tests, but release waits for both.

**48-hour/two-day cutoff:** stop at the tested local/read-only evaluation build. Disable task/campaign mutations unless D2-2 is complete. No hosted release before D3 gates, even if a URL can be created earlier. **Solo schedule:** use the first 16–24 hours for scope, semantics, limits and regression; defer OIDC/hosting or writes as needed. Do not claim the two-engineer scope fits one developer.

## Baseline already verified

- [x] Read the complete application source and test suite, repository guidance, launcher and existing plans.
- [x] Compare current product positioning with official Shopify, Gorgias, Intercom, Zoho and HubSpot pages; sources and caveats are in production plan section 0.
- [x] Run `powershell -ExecutionPolicy Bypass -File .\run.ps1 -CheckOnly`: **16 passed in 2.84s**, 2026-10-04, baseline commit `1e6eb75`.
- [x] Day 1 local implementation evidence is recorded below. No hosted-pilot or production gate is inferred from it.

## Day 1 — establish safe boundaries

### D1-1 — lock scope and acceptance (A, 1h; RQ02/03)

- [x] Record the synthetic dataset, proposed hosting/model/budget boundary and pending owner/evaluator decisions in a nonsecret decision note.
- [x] Select one representative commerce workflow: low stock → evidence → review task → verify task; finance and growth remain explicitly scoped demo functions.
- [x] Confirm no real merchant source/account is required for this sprint. Record discovery questions from production plan section 22 as deferred dependencies.
- [ ] Obtain a 30-minute merchant review slot; if unavailable, report engineering evaluation only, not customer validation.

Done: reviewer can name what the release supports, excludes, costs and tests. Dependency: none.

### D1-2 — authentication and shared authorization (B, 5h; RQ01)

- [x] Pin a tested Streamlit version supporting OIDC and add a secret-template configuration.
- [ ] Configure the real managed identity client and HTTPS callback in the deployment secret store.
- [x] Add a server-side allowlist keyed by trusted issuer/subject; never trust a typed email, URL parameter, model argument or display name.
- [x] Gate all dashboard/database/AI access before initialization/rendering. Create shared actor-context checks used by UI actions, online tools and offline mode.
- [x] Recheck allowlist/session expiry before each action; clear chat/context on logout or identity change. Set an explicit short application session policy independent of the identity cookie.
- [x] Add automated denial tests for missing, unlisted, expired and revoked actors and prove denial occurs before the model call. Direct SDK tool invocation is part of the Day 2 wrapper tests.

Done: local tests prove fail-closed behavior; real OIDC callback/logout/multiple-tab checks are still D3-2. Missing identity-provider credentials blocks hosted access, not local synthetic work. Dependency: D1-1 identity policy.

### D1-3 — data mode and evidence (A, 3h; RQ02)

- [x] Add explicit deployment/data settings. Only demo mode may seed; a missing non-demo database fails clearly without inserting fictional records.
- [x] Show source label, dataset version/seed time and query time separately. Never label a snapshot as live.
- [x] Reduce owner summary to counts and bounded evidence; omit inactive-customer names/preferences unless a specific authorized query requires them.
- [x] Set bounded result sizes (initial proposal 50 rows) and return a truncation flag. Do not compute aggregate counts from a truncated list.
- [x] Test demo/non-demo startup, capped rows, aggregate counts and absence of unnecessary personal fields. Empty/error UI tests continue in D2-4.

Done: every supported answer has usable dataset/date evidence and truthful limitations. Dependency: D1-1; agree policy interface with B.

### D1-4 — correct domain semantics (A, 3h; RQ03)

- [x] Replace calendar cash-flow claims with explicit order-cohort receipts/receivables and dated expenses. Apply to UI, prompts, offline replies and documentation.
- [x] State that payment dates, opening balance, fees/refunds and full outstanding balances are not modeled. Do not implement a ledger in this sprint.
- [x] Add independent cases for existing statuses/partial receipts plus an older-order receipt, empty/invalid ranges and Bangladesh timezone boundary.
- [x] Reject nonexistent related inventory IDs and whitespace-only task titles before persistence; test valid/invalid entity references.

Done: independent fixtures validate the stated metric; no misleading "cash received today" remains. Dependency: D1-1 definitions.

### D1-5 — reproducible build and secret hygiene (B, 2h; RQ07)

- [x] Add tested dependency constraints/lock and Python version; record relevant package versions in repository files.
- [x] Ignore `.streamlit/secrets.toml`; ensure templates contain placeholders. Scan tracked files and history with redacted output.
- [x] Add CI for offline tests and dependency/secret scanning with no production credentials. Remote CI execution remains pending until changes are pushed.
- [x] Keep `run.ps1` a development launcher. Deployment starts the tested app artifact without installing packages or seeding on each request.

Local checkpoint done: the locked current environment passes offline tests and secret scanning. Clean-machine and remote-CI evidence remain required. Dependency: D1-2 chosen dependencies.

### Day 1 checkpoint evidence

- Local environment: Python 3.13.2, Streamlit 1.64.0, OpenAI Agents SDK 0.22.3, Pydantic 2.13.5.
- `pytest`: **26 passed in 2.38 seconds** after the Day 1 changes.
- Streamlit AppTest smoke: one title rendered and zero exceptions in demo mode.
- Secret scan: tracked files and Git history patches passed; values are never printed.
- Lock validation: every locked package resolved from the current environment using `pip --dry-run`.
- `git diff --check`: passed; Git only reported expected Windows LF/CRLF conversion warnings.
- Product owner approved Google OIDC, Gemini, a provisional USD 2/day live-evaluation budget, and up to two evaluators. Evaluator identifiers, host, real OIDC callback, remote CI, clean-machine build and Day 3 release gates remain pending.

## Day 2 — bound behavior and verify workflows

### D2-1 — model limits, usage and failure handling (B, 4h; RQ04)

- [x] Enforce initial configurable limits: 2,000-character message, bounded recent history plus 12,000-character context ceiling, 50-row/size-capped tool results, four model calls, six tool calls, 30-second overall deadline and bounded output tokens. Test actual adapter enforcement; SDK `max_turns` alone is insufficient.
- [x] Allow one active model run per owner and two globally. Persist request admission/usage in SQLite so restart does not reset the daily allowance.
- [x] Configure the approved USD 2/day synthetic-evaluation budget. Reserve conservative token cost atomically; include retries/in-flight reservations; record unknown usage for reconciliation.
- [x] Fail closed when model pricing/configuration is unknown. Provider alerts supplement application bounds; do not promise an exact invoice cap.
- [x] Disable payload tracing by default for every provider. Sanitize errors and log run IDs/categories rather than keys/prompts/tool payloads.
- [x] Handle 401/403/429/timeouts/unavailable model appropriately. Retry at most one eligible transient failure within the same deadline/budget; no retry for bad credentials. No silent provider or offline fallback.
- [x] Test with a fake provider: no real network in deterministic tests; prove adapter limits, simultaneous budget admission, timeout, restart persistence, authentication failure release and no fallback.

Done: failed/expensive runs stop predictably and UI states are truthful. Dependency: D1-2/3/5. If budget/timeout enforcement cannot be completed, ship deterministic read-only mode and label AI unavailable.

### D2-2 — confirmed internal writes (A, 4h; RQ05)

- [x] For the pilot, make model write tools propose task/campaign drafts for explicit owner confirmation. UI buttons and offline mode use the same execution gate.
- [x] Bind confirmation to actor, action and exact normalized payload; recheck authorization at execution. Edited proposals require new confirmation.
- [x] Persist logical-request idempotency keys and reject reuse with different payload. General tasks/campaigns do not duplicate on rerun; restock still uses its unique index.
- [x] Persist campaign objective. Add actor/action/outcome/time audit records without customer text or secrets.
- [x] Test replay, double-click, changed payload, denied actor, database failure and parallel restock calls. Require one logical mutation and a truthful success/pending/failure result.

Done: enabled mutations have passing gate/replay tests. Dependency: D1-2/4. If incomplete, remove mutation tools and buttons from the release; maintain a read-only pilot.

### D2-3 — scoped language evaluation (B, 3h; RQ06)

- [x] Retain the 26 existing cases as regression prompts; adapt mutation expectations to the confirmation flow.
- [x] Add 18 held-out cases: six English, six Bangla, six Banglish; include ambiguity, missing data, stale evidence, injection and follow-up references. Keep context-linked cases together.
- [x] Record expected tool/arguments, fixture facts, permitted write status and unacceptable claims. Do not tune on the holdout after seeing results without creating a new holdout.
- [x] Prepare a runner/report capturing actual tool events, grounded values, latency and provider usage with synthetic data only. A human reviews language and action claims.

Done: evaluation is executable/reviewable; live execution is D3-3 and requires provider access/budget. This small set does not prove general multilingual production quality or replace the later 500-case benchmark.

### D2-4 — UI regression and operating instructions (A, 3h; RQ06/07)

- [x] Add Streamlit AppTest coverage for invalid configuration, mode/evidence labels, numeric cards and confirmation UI; use browser checks for OIDC/network flows AppTest cannot prove.
- [x] Ensure unsupported dates/intents in offline mode state their limitations; no false claim that a campaign was sent or purchase completed.
- [x] Test repeated reruns without repeated actions and session-history version clearing. Real OIDC identity clearing, Bangla rendering and mobile-width checks remain D3 browser work.
- [x] Update README and prototype overview: true test results, scoped finance definitions, no hallucination guarantee, local/demo/pilot distinction, locked setup and Day 3 limitations.

Done: one written happy path and the failure paths match the shipped UI. Dependency: D1 and integrated D2 controls.

Day 2 evidence (2026-10-04): `44 passed in 6.13s` using a workspace-local pytest temp directory; the offline evaluation runner executed all 44 regression/holdout cases. Offline execution verifies the runner and deterministic routes only, not live model quality. “Today” finance is now dated by the Bangladesh backend clock and bypasses model date generation.

## Day 3 — integrated tests, staging and release decision

### D3-1 — deterministic integration and security gate (A, 4h; RQ01–07)

- [x] Run existing and added deterministic tests from a clean environment, with all external inference blocked/faked.
- [x] Test direct/indirect injection in stored product/task text; it cannot grant tools, bypass actor checks or execute an unconfirmed write.
- [x] Repeat simultaneous restock and request-admission tests against the release DB adapter; verify exact counts and handled failures.
- [x] Run static/dependency/secret scans; triage all findings. A reachable high/critical issue or secret exposure blocks hosted release until resolved.
- [x] Record command, commit, environment, pass/fail counts and failure evidence. A coverage percentage alone is not acceptance.

Local evidence: the supported Windows launcher passed 51 tests in 8.46 seconds; a fresh Linux container passed the same 51 tests in 7.57 seconds. Ruff `E9,F`, Bandit, dependency audit and the final secret scan passed. The dependency audit found `PYSEC-2026-4141` in PyJWT 2.14.0; the lock was upgraded to 2.15.0 and the rerun found no known vulnerabilities. Container health and all eight pilot preflight checks passed.

Dependency: integrated D2 build. Done: all applicable matrix rows below pass.

### D3-2 — staging, persistence and real authentication (B, 4h; RQ07)

- [ ] Deploy one tested instance to an approved host with HTTPS, secrets and persistent disk; set two-evaluator allowlist. Use synthetic data only.
- [ ] Exercise OIDC valid/invalid login, direct page access, logout, expired session, removed allowlist entry and multiple open tabs in a real browser. Test callbacks/redirect configuration.
- [ ] Create an allowed internal task, restart the process, and verify persisted state. Do not treat successful page load as a persistence test.
- [ ] Back up SQLite with its supported backup API; restore to a separate path and compare critical row counts/records, schema and audit state. Do not copy an active DB file blindly.
- [ ] Rehearse application rollback to the previous tested artifact/config without destructive DB downgrade; verify the same smoke flow.
- [ ] Write a short runbook for provider outage, budget exhaustion, failed startup, restore and disabling access. Name the business-hours operator.

Local recovery preparation is complete: supported SQLite backup/restore matched counts and logical digests for all 11 critical tables, and persistence across separate processes passed. The runbook is written. This hosted gate remains open until an operator is named and restart, restore, rollback and OIDC are exercised on the deployed service.

Done: measured restart/restore/rollback evidence. No SLA or RPO claim inferred. Dependency: D1 auth/build and D3-1 pass before release. Missing host/disk/OIDC access means local or disposable read-only synthetic demo only.

### D3-3 — live model and owner acceptance (A, 3h; RQ06/07)

Recorded v3 artifacts contain 112,732 input tokens, 4,162 output tokens, 65 model calls and 33 tool calls. At the official 2026-10-08 paid standard price for `gemini-3.1-flash-lite`, the visible-token estimate is USD 0.034426; eligible free-tier billing may be zero. This is a lower bound because setup calls, timed-out attempts, earlier diagnostics and provider retries are not all retained. Provider-console reconciliation is still pending.

- [ ] With approved synthetic-data key/budget, execute the 26 regression prompts and 18 holdout cases through the actual chosen provider/model. Record repeated calls and cost; do not call this deterministic testing.
- [x] Require all safety/action-status cases to pass, exact supported financial facts, and at least 17/18 correct holdout tool/argument and grounded responses, with at least 5/6 per language. v3 passed 17/18: English 6/6, Bangla 5/6 and Banglish 6/6; regression passed 26/26. Small-sample uncertainty remains.
- [x] Inspect actual tool traces and retain failed predeclared expectations rather than retroactively changing them. The sole v3 holdout failure safely declined an empty-segment campaign but remains recorded as failed.
- [ ] Demonstrate login → inventory evidence → confirmed internal task (if enabled) → repeated request without duplicate → provider failure → still-available deterministic dashboard.
- [x] Project Owner approved the v3 language/action review for the restricted synthetic pilot on 2026-10-08. Three minor language/empty-segment notes remain documented; no silent offline substitution was used.

Dependency: D2-3 runner and stable staging. Provider/network/403/quota limitation is reported as **not tested**, not passed. Do not spend the whole sprint repeatedly replacing keys.

### D3-4 — bounded load and release evidence (B, 3h; RQ04/07)

- [ ] Use two concurrent browser sessions for 15 minutes with scripted dashboard interactions and fake-provider chat including a 30-second delay. Verify no cross-session chat bleed, duplicate writes, uncaught DB locks or bypassed model admission.
- [ ] Measure non-model UI completion (proposed p95 <2 seconds in this small environment), deadline behavior and error counts. This is a pilot envelope, not an R1 capacity benchmark.
- [ ] Capture one deployed real-model smoke separately; do not load-test a paid provider without an explicit budget.
- [x] Collect the available CI-equivalent local report, security triage, recovery results, load result and enabled-feature list in a release record; explicitly mark live evaluation, deployed auth/browser and hosted restart/rollback evidence as pending.
- [ ] Release owner reviews gates. Promote the same tested artifact only if applicable requirements pass; otherwise document local/read-only/offline fallback and remaining tickets.

The 15-minute two-session backend harness passed: 30,000 dashboard operations, p95 15.65 ms, zero errors, isolated session histories, expected write counts and no remaining model reservations. It used simulated sessions rather than real browsers, so the first two checklist items remain open. Release evidence has been collected in [docs/releases/2026-10-04-day3.md](docs/releases/2026-10-04-day3.md); owner review remains pending.

Dependency: D3-1/2 and A's evaluation results. Done: an evidence-backed go/no-go decision, not merely a deployment URL.

## Required test matrix

| Suite | Essential assertion | Release consequence |
|---|---|---|
| Existing 16 tests | No unexplained regressions; intentionally changed expectations documented | Any unexplained failure blocks release |
| Auth/policy | No DB/model/tool access for unauthorized actor; revocation applies to new actions | Hosted pilot blocked |
| Finance/domain | Independent fixed expected values, cohort labels, dates and valid entity references | Affected reporting/writes blocked |
| Data mode | No fictional seed in non-demo mode; freshness/source explicit | Real-data use remains blocked |
| Mutation replay | One logical task/draft; altered confirmation rejected; parallel restock safe | Disable writes if failing |
| Provider contracts | Error mapping, deadline, bounded calls/results, output cap and no silent fallback | Disable AI if failing |
| Cost controls | Atomic reservations survive concurrent requests/restart; unknown usage retained | Disable paid AI if failing |
| Injection/redaction | Input cannot gain authority; no keys/PII in default traces/errors | Hosted AI blocked |
| UI/browser | Auth, empty/errors, Unicode, session isolation and truthfully displayed status | Affected hosted flow blocked |
| Deployment/recovery | Restart keeps permitted state; tested restore and rollback | No durable hosted-pilot claim |
| Live evaluation | Safety and numeric facts pass; 17/18 holdout, >=5/6 per language | Disable model or fix and reevaluate |
| Small-load test | Two sessions/15 minutes; correct state and admission under delayed provider | Reduce scope or fix before hosted release |

Future-feature tests are mandatory when those features ship: real PostgreSQL RLS/pool isolation, two-tenant API/worker/cache/RAG access, connector snapshots/deletes/out-of-order replay, payment reconciliation, approval revocation, document deletion, customer identity and external side-effect recovery. They cannot be reported passed on this SQLite owner prototype. Full requirements are in production plan section 16.

## Commands and evidence

Existing supported Windows command, from `ai-agent-business`:

```powershell
powershell -ExecutionPolicy Bypass -File .\run.ps1 -CheckOnly
```

It installs dependencies and initializes the configured demo database before tests. Run only against a development/demo configuration, never a production database. Added tests should be discoverable by this same pytest invocation. CI should install locked dependencies and run tests with a fresh temporary database without using the seeding launcher as a production start command.

The evaluation runner is available as `python evals/run_evals.py --suite all`; add `--live` only after the Day 3 provider gate and use `--output docs/releases/live-eval.json` to save the redacted report. Real-browser and bounded-load commands remain Day 3 work. Save release evidence as `docs/releases/<date>-pilot.md` with: commit/artifact digest, Python/package versions, enabled features, test counts, model ID and evaluation sample, measured cost/latency, authentication checks, restore duration, unresolved limitations and release decision. Exclude secrets and raw private data.

## No-go rules and scope cuts

1. No managed identity/verified authorization: local synthetic evaluation only.
2. No persistent disk/restore proof: disposable synthetic read-only demo; no durability promise.
3. No reliable provider access or usage bounds: deterministic dashboard/offline mode explicitly labeled; model acceptance incomplete.
4. Write races/confirmation/replay failures: remove write tools and buttons, retain reads.
5. Any real-data, public consumer or second-merchant requirement: return to full production phases; do not bypass isolation/privacy work to meet the deadline.
6. Unresolved security or correctness failure in an enabled feature: no release for that feature. Additional time is preferable to marking a failing gate complete.

## Next work after this sprint

- [ ] Complete merchant discovery and source contract; validate willingness to pay and incumbent comparison.
- [ ] Implement PostgreSQL/auth/membership/RLS foundation and two-tenant tests (phase B).
- [ ] Connect one source with backfill, deltas, deletion handling and reconciliation (phase C).
- [ ] Build customer identity, lead/draft-order and human handoff workflows (phase D).
- [ ] Run larger held-out language/security benchmarks and cost/reliability gates (phase E).
- [ ] Launch controlled real-data R1 with operational signoff (phase F).
- [ ] Add R2–R4 capabilities only when demand, data, permissions and testing justify them.

# BizPilot AI - November Merchant Prototype Plan

Updated: 2026-10-11. Target: a merchant demonstration in November 2026.
Exact meeting date and named teammates: to be confirmed by the Product Owner.

## Implementation tracker

| Checkpoint | State | Evidence |
|---|---|---|
| Plan refinement | Complete | This document |
| Day 1 - scope and data rules | Approved 2026-10-11 | [Scope freeze](docs/NOVEMBER_DEMO_SCOPE.md) |
| Day 2 - fixtures and expected results | Approved 2026-10-11 | [Fixture results](docs/NOVEMBER_DEMO_FIXTURE_RESULTS.md) |
| Day 3 - controlled staging inventory seed | Approved 2026-10-12 | [Seed evidence](docs/NOVEMBER_DEMO_DAY3_RESULT.md) |
| Day 4 - malware scanner selection | Approved 2026-10-12; paid deployment deferred | [Scanner decision](docs/decisions/0011-november-demo-malware-scanner.md) |
| Day 5 - dormant scanner wiring and cleanup | Approved 2026-10-12 | [Day 5 result](docs/NOVEMBER_DEMO_DAY5_RESULT.md) |
| Day 6 - offline classification and safe rendering | Approved 2026-10-12 | [Day 6 result](docs/NOVEMBER_DEMO_DAY6_RESULT.md) |
| Day 7 - inventory UI and state polish | Approved 2026-10-12 | [Day 7 result](docs/NOVEMBER_DEMO_DAY7_RESULT.md) |
| Day 8 - tenant-scoped business facts | Approved 2026-10-12 | [Day 8 result](docs/NOVEMBER_DEMO_DAY8_RESULT.md) |
| Day 9 - grounded Copilot integration | Approved 2026-10-12 | [Day 9 result](docs/NOVEMBER_DEMO_DAY9_RESULT.md) |
| Day 10 - restock review and offline behavior | Approved 2026-10-12 | [Day 10 result](docs/NOVEMBER_DEMO_DAY10_RESULT.md) |
| Day 11 - multilingual evaluation | Approved 2026-10-12 | [Day 11 result](docs/NOVEMBER_DEMO_DAY11_RESULT.md) |
| Day 12 - changed boundaries and failure paths | Approved 2026-10-12 | [Day 12 result](docs/NOVEMBER_DEMO_DAY12_RESULT.md) |
| Day 13 - candidate and recovery preparation | Approved, pushed and deployed 2026-10-12 | [Day 13 result](docs/NOVEMBER_DEMO_DAY13_RESULT.md) |
| Day 14 onward | Not started | Continue with zero-cost reduced scope below |

## 1. Purpose and realistic timeline

Deliver a repeatable ten-minute walkthrough: sign in, inspect inventory, explain
the safely disabled CSV preview, ask five business questions and review a
restock proposal.

The filename is retained for continuity. This replaces the original one-week
build estimate with **15 working days of delivery plus a final seven-calendar-day
preparation window**. Estimate assumes one developer with 5-6 focused hours per
working day and timely Product Owner/reviewer decisions. Part-time work, missing
data or unresolved scanning infrastructure can extend it to four weeks or more.

Illustrative calendar: build October 12-30, 2026, with November 2-8 reserved for
rehearsal and a possible meeting. This assumes Monday-Friday working days;
adjust to the team's calendar and the actual merchant meeting. Dates are a
planning assumption, not a confirmed commitment. An earlier meeting requires
an explicitly reduced scope.

## 2. Current baseline and evidence limits

| Area | Recorded baseline | Remaining demo work |
|---|---|---|
| Auth0, HTTPS and workspace | Staging web/API and managed login established | Reuse setup; smoke-check the selected release |
| Authorization | Restricted database roles, RLS and membership/role checks | Apply tenant authority to each new tool |
| Sessions | Redis storage and provider revocation implemented | Verify availability and recovery before rehearsal |
| Inventory | Read API, search/filter and empty states exist | Seed representative data and verify displayed results |
| CSV preview | Parser, metadata, UI and dormant ClamAV adapter exist | Keep deployed processing disabled at zero cost; activate after funded private scanner review |
| Copilot pilot | README documents SQLite tools, proposals and offline mode | Verify/reuse logic and integrate the merchant web workflow |
| Phase 1H | Repository records restricted staging acceptance | Carry forward the feature-specific evidence gaps below |

References: [Phase 1H](docs/PHASE_1H_BROWSER_VALIDATION.md),
[release record](docs/releases/2026-10-11-phase1h-staging.md),
[CSV decision](docs/decisions/0007-phase1-inventory-import-preview.md),
[existing pilot](README.md).

Evidence qualification: the deployed CSV run observed a sanitized 503, but its
original test stopped before the XSS assertions executed. The revised assertion
was not rerun in that session. Enabled preview rendering therefore still needs
a real test. The passing oversized-upload test covered declared Content-Length
at the BFF; it did not establish proxy limits, streaming-body protection or rate
limits. Cold-start recovery is not a controlled outage/log-redaction exercise.
Schedule these specific checks below without restarting completed auth setup.

## 3. Scope and merchant experience

One approved account uses one workspace with labeled demonstration data:

1. Sign in and see populated inventory, source and observation time.
2. Search a SKU and filter products needing attention.
3. Explain that CSV preview is safely disabled until private malware scanning is funded.
4. Show the prepared offline classification evidence without presenting it as a live upload.
5. Ask five supported questions in natural language.
6. Review a restock proposal containing quantities, rationale and source facts.

Use **one Copilot with Operations, Growth and Finance tools**. The 18-agent
catalogue remains future product scope. Existing pilot write capabilities are
not automatically enabled in this demonstration; proposals stay review-only.

| Supported question | Deterministic source | Acceptance |
|---|---|---|
| Which products need restocking? | Inventory balances and approved thresholds | Correct SKU list and quantities |
| Show today's financial summary. | Order/expense fixture and documented finance definitions | Correct totals, period and limitations |
| Which customers have been inactive? | Pseudonymous customers, order history and explicit inactivity window | Correct cohort/count without unnecessary contact details |
| What tasks need attention? | Task fixture, statuses and due dates | Correct unfinished/overdue list |
| Prepare a restock review proposal. | Inventory results and explicit suggested-quantity rule | Evidence visible; nothing executes |

Test all five in English, Bangla and Banglish. Python/SQL calculate business
facts; the model explains them. Missing source data produces an unavailable
answer. A campaign proposal is optional after the required restock flow passes.

Deferred: live Shopify/WooCommerce/POS synchronization, inventory apply,
purchasing, payments/refunds, messaging, billing, multi-workspace switching,
advanced RAG, the 18-agent implementation and production rollout.

## 4. Dataset and business definitions

Inventory CSV does not contain customer, finance or task history. Prepare those
as separate sanitized fixtures and label their sources accurately.

| Dataset | Preparation target | Expected-result record |
|---|---|---|
| Inventory | 10-30 products, representative variants/SKUs, 1-2 locations | Normal, low and zero stock; exact totals |
| Preview CSVs | Valid/new, changed, duplicate, invalid and stale-version cases | Expected classifications and errors |
| Orders/customers | Small pseudonymous history across activity and order statuses | Expected financial values and inactive cohort |
| Expenses/tasks | Small dated fixture | Expense totals and unfinished/overdue tasks |

Use synthetic data unless the merchant explicitly approves sanitized data.
Exclude credentials and unnecessary names, phone numbers and email addresses.
Record dataset version, source, observation time, `Asia/Dhaka` timezone and BDT.
Freeze a reference date for rehearsals; if showing a fixed demo date, label it.
Otherwise November changes the meaning of 'today', 'inactive' and 'overdue'.

Reuse finance definitions in README: confirmed/delivered orders count as sales;
pending/cancelled orders do not. Receipts/receivables use the documented
order-cohort model. Do not describe this as complete accounting, profit or cash
flow without the missing inputs. Confirm threshold equality, inactivity duration,
overdue rules and restock suggestion formula with the Product Owner on Day 1.

**Seed inventory separately from CSV preview.** Build a controlled, repeatable
seed for the dedicated workspace, with known counts and reset/rollback steps.
Preview must never populate or change inventory. Privileged seed credentials
must not become application runtime credentials.

SQLite pilot and PostgreSQL staging are separate data paths. Primary web-demo
tools must use the selected tenant's staging data. Until integrated, present
the protected SQLite pilot as a separately labeled fallback; never silently
mix its business facts into a staging workspace's answers.

## 5. Owners and resources

Assign names at kickoff. One person may cover multiple roles.

| Role | Responsibility | Required availability |
|---|---|---|
| Product Owner | Meeting date, merchant type, data approval, business rules and acceptance | Resolve blocking decisions within one working day |
| Developer | Fixtures, backend/UI, tests and deployment preparation | 5-6 focused hours per working day assumed |
| Reviewer/teammate | Independently compare results and perform rehearsal | Weekly review plus final rehearsal |
| Demo operator | Present workflow and collect feedback | Practice on the actual presentation device |

Required resources:

- Existing repository, local development tools and CI access.
- Existing Auth0 application, Supabase database and Render web/API/session services.
- A funded local/private malware scanner is required only when live CSV preview is activated.
- Server-side model credentials, model verified at implementation and agreed usage cap.
- Fixture pack, expected-answer sheet and dedicated demo account.
- Health-check instructions, backup storage and disposable restore target.
- Presentation device, internet, backup connection and approved recording location.

Before buying infrastructure, record current quoted costs for hosting/session
persistence, scanner hosting and model usage; obtain the Product Owner's monthly
cap. No purchase is assumed by this plan. Evaluate always-on hosting for the
meeting. If free hosting is retained, measure warm-up/recovery and rehearse the
fallback. No exact provider price is assumed here.

## 6. Delivery schedule: 15 working days

| Day / example date | Work and dependencies | Deliverable and exit evidence |
|---|---|---|
| 1 / Oct 12 | Owner + developer freeze workflow, data rules, meeting window and roles | Approved scope, reference date and expected question types |
| 2 / Oct 13 | Developer prepares fixtures; reviewer checks arithmetic | Versioned fixture pack and expected answers |
| 3 / Oct 14 | Developer implements controlled seed and tenant-scoped reads | Populated inventory; repeat seed does not duplicate rows; reset documented |
| 4 / Oct 15 | Developer reviews scanner adapter and hosting | Clean/rejected file, timeout, service failure and signature freshness behavior tested |
| 5 / Oct 16 | Developer prepares dormant scanner configuration and metadata purge; paid scanner deployment remains deferred | Future activation path is tested; staging preview stays safely disabled at zero cost |
| 6 / Oct 19 | Developer + reviewer exercise parser classifications and rendering offline | New/changed/duplicate/stale/invalid cases correct in tests; stock unchanged; live upload remains disabled |
| 7 / Oct 20 | Developer polishes populated inventory and permission/error states | Desktop/mobile usable; source and timestamp clear |
| 8 / Oct 21 | Developer connects tenant-scoped finance/customer/task tools | All five questions have deterministic sources; applicable object-isolation tests pass |
| 9 / Oct 22 | Developer connects Copilot UI and approved model | Grounded answers with source context; missing-data behavior verified |
| 10 / Oct 23 | Developer adds restock review and offline behavior | Proposal has reviewed quantities/evidence; no external action; offline mode labeled |
| 11 / Oct 26 | Reviewer runs language evaluation | At least 15 prompt cases checked across English, Bangla and Banglish |
| 12 / Oct 27 | Developer checks changed boundaries and failure paths | Applicable role/tenant/upload tests pass; controlled API/provider failure and safe logs verified |
| 13 / Oct 28 | Developer deploys candidate and prepares recovery | Candidate SHA, passing CI, disposable backup restore and rollback instructions |
| 14 / Oct 29 | Operator + reviewer rehearse twice | Two successful clean-browser walkthroughs; fallback recording prepared |
| 15 / Oct 30 | Team fixes blockers and freezes candidate | Acceptance record, known limitations and operator instructions complete |

Current zero-cost dependency chain: approved fixtures -> seeded/readable
inventory -> integrated tools -> grounded Copilot -> rehearsal. Scanner/upload
activation remains a separate funded track and live preview cannot be marked
complete until that track's dependencies pass.

If blocked for more than one working day, record the owner, next action and
schedule impact. Agree scope changes explicitly; do not silently replace a
required live feature with a screenshot.

## 7. Final seven-day preparation window

Use relative dates once the meeting day (`T`) is confirmed.

| When | Owner/action | Ready when |
|---|---|---|
| T-6 | Developer freezes features and checks deployment | Candidate/config changes recorded; no demo blocker |
| T-5 | Reviewer checks data/date-sensitive answers | Fixture labels and expected values consistent |
| T-4 | Developer checks recovery instructions | Backup/restore evidence and rollback available to operator |
| T-3 | Operator rehearses on actual device/network | Complete workflow without developer intervention |
| T-2 | Team records fallback and fixes only blockers | Recording/offline mode opens and is clearly labeled |
| T-1 | Owner confirms meeting; operator checks account/network | Clean sign-in and presentation setup work |
| T | Operator checks services 30 minutes before and presents | Feedback recorded and next pilot decision discussed |

After late fixes, rerun affected checks and the walkthrough. Known data-isolation
or security failures block merchant access.

## 8. Ten-minute walkthrough

| Time | Action | Merchant takeaway |
|---|---|---|
| 0:00-1:00 | Explain source/date, sign in and open workspace | Clear context and ownership |
| 1:00-2:30 | Search SKU and show low/zero stock | Operational visibility |
| 2:30-3:00 | Explain the disabled CSV control and show labeled offline test evidence | Safe boundary and future capability are clear |
| 3:00-7:00 | Ask five rehearsed questions | Answers match known facts |
| 7:00-8:30 | Inspect restock proposal and evidence | Merchant reviews suggested next step |
| 8:30-10:00 | Explain limitations and request feedback | Identify a useful limited pilot |

Ask which insight matters, which data export the merchant uses, what is missing
and whether they would try a limited pilot. Avoid storing unnecessary personal
data in meeting notes.

## 9. Acceptance checklist and verification discipline

Record candidate SHA, dataset version, reference date, reviewer, actual result
and redacted evidence location. A check passes only after its assertions execute.
A disabled preview's 503 proves denial, not successful preview or safe rendering
of returned content.

- [ ] Approved account sees only its intended workspace.
- [ ] Seeded inventory and summaries match the fixture.
- [ ] Offline parser tests classify valid/new/changed/error/conflict cases correctly.
- [ ] Deployed preview remains unavailable and does not accept or retain raw uploads.
- [ ] Dormant scanner adapter tests cover rejection, outage, timeout and malformed responses.
- [ ] Live preview, freshness, rate limits, purge and enabled-rendering XSS checks remain recorded as funded follow-up work.
- [ ] Five questions have correct facts across three language variants.
- [ ] Missing data and provider failure are clear; offline mode is labeled.
- [ ] Restock proposal has evidence and no executable external action.
- [ ] Desktop/mobile and controlled failure states are usable.
- [ ] No secrets/tokens appear in UI or ordinary logs; temporary auth files are removed.
- [ ] Candidate CI, relevant local tests, restore and rollback evidence are complete.
- [ ] Two clean-browser rehearsals pass and backup material is ready.
- [ ] Owner and reviewer record readiness and known limitations.

Reuse auth evidence where behavior is unchanged. For implementation changes,
run applicable repository checks, including `run.ps1 -CheckOnly` as required by
AGENTS.md, and relevant frontend tests. Broaden/repeat security checks only for
changed behavior, failure or a concrete unresolved risk. Batch login-dependent
checks so the merchant does not repeatedly capture sessions during routine work.

## 10. Fallback and release decisions

| Problem | Response | Consequence |
|---|---|---|
| Scanner/preview unavailable | Keep upload disabled and use the approved inventory/Copilot-only demonstration | Full plan remains incomplete; reduced scope is disclosed |
| Model unavailable | Use tested, labeled offline answers from approved facts | Acceptable only if rehearsed |
| Web/API unavailable | Follow recovery instructions; present labeled recording or protected pilot | Live web demo unavailable; record follow-up |
| Session store loses state | Sign in again after recovery | Check access; do not bypass authentication |
| Merchant data unavailable | Use approved synthetic fixtures | Demonstrates workflow, not merchant-specific outcomes |
| Wrong totals or tenant exposure | Stop affected flow and fix | Release blocker |

Completing this plan yields a merchant demonstration. A production pilot needs
separate scope, durable hosting/recovery, monitoring, support, privacy operations
and reviewed write workflows. Keep the 18-agent roadmap in the long-term product
plan.

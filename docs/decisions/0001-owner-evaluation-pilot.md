# Decision 0001: Restricted Owner Evaluation Pilot

Date: 2026-10-04

## Decision

The immediate deliverable is one synthetic-data owner evaluation pilot. Its
representative workflow is: inspect low-stock evidence, propose or confirm an
internal restock-review task, and verify the saved task without creating a
duplicate. Finance and growth remain explicitly limited demonstrations.

The pilot permits at most two named evaluators. OIDC authenticates them and an
`issuer|subject` server allowlist authorizes owner access. Names and email
addresses are not authorization identifiers. Real merchant data, customer
access, messaging, payments, publishing, uploads, RAG, fine-tuning and People
features are excluded.

The data source is `fictional-v1`. The application must show its source,
snapshot time and query time. It may use Gemini or OpenAI only with synthetic
data, bounded usage and an approved credential. Offline mode remains clearly
labeled. The product owner approved Gemini for the pilot with a provisional
live-evaluation model budget of USD 2/day. The application reserves usage
before each run and persists usage locally; this is an application control,
not a guarantee of the provider invoice total.

## Pending checkpoint decisions

- Evaluator OIDC `issuer|subject` identifiers: pending; do not put secrets here.
- Identity provider: Google OIDC approved; client configuration remains pending.
- Pilot host with HTTPS and persistent disk: pending.
- Live model/provider and budget: Gemini and USD 2/day approved.
- Merchant review slot: pending; without it, report engineering evaluation only.

## Consequences

The local demo keeps automatic fictional seeding. Pilot startup never creates
or seeds a database. The synthetic database must be provisioned explicitly and
stored on persistent disk. Missing identity, allowlist, database or provider
access fails clearly. A working public URL alone is not release evidence.

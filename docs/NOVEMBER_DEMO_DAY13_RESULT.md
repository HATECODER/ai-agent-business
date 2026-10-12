# November demo Day 13 result

Date: 2026-10-12
Status: approved, pushed and deployed

Candidate commit: `5180b592574ed55d5d7ab6ac4764aa93696dbeca`

## Candidate contents

- Approved Day 1-12 November demo scope, fixtures, database readers, Copilot UI,
  restock review, multilingual evaluation and failure-path protections.
- Free-tier staging configuration keeps CSV preview disabled while preserving
  the dormant ClamAV activation path.
- No secret, local authentication state, generated PDF, temporary test folder
  or SQLite demo database belongs in the candidate commit.

## Recovery preparation

[`NOVEMBER_DEMO_RECOVERY.md`](NOVEMBER_DEMO_RECOVERY.md) records:

- the application rollback order for Render web/API;
- the currently affordable reconstruction path for synthetic staging data;
- exact post-recovery expected values;
- the limitation that a full managed PostgreSQL backup/restore drill remains a
  funded production-pilot requirement.

The controlled seed commands already rehearse each database transaction with a
rollback before applying. Day 3 and Day 8 recorded successful staging execution.

## Candidate verification

Before creating the local release commit:

- supported repository check: passed;
- frontend unit tests, typecheck and production build: passed;
- targeted Ruff and Bandit checks: passed;
- multilingual evaluation: 15/15 passed;
- diff whitespace check: passed;
- secret scan and tracked-file review: required immediately before commit.

GitHub Actions
[`offline-checks` run 38226411488](https://github.com/HATECODER/ai-agent-business/actions/runs/38226411488)
completed successfully for the exact candidate commit. Its `test`,
`postgres-rls`, `frontend` and dependent `docker` jobs all passed.

Render auto-deployment was then observed through the new candidate behavior:

- `GET https://bizpilot-hatecoder-staging-web.onrender.com/copilot` returned
  `200`;
- an unauthenticated valid request to
  `POST https://bizpilot-hatecoder-staging-api.onrender.com/api/v1/copilot/query`
  returned the expected sanitized `401` rather than `404`.

Authenticated five-question browser rehearsal remains Day 14 work.

## Approval boundary

The Product Owner explicitly approved the Day 13 push. No database credential,
schema write or fixture reseed was required during this deployment.

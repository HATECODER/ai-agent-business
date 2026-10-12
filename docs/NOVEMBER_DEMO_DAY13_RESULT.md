# November demo Day 13 result

Date: 2026-10-12
Status: local candidate prepared; awaiting Product Owner push/deploy approval

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

The final local commit SHA is reported by the operator after the commit is
created. Remote CI and Render deployment cannot be claimed until the candidate
is pushed and those services finish successfully.

## Approval boundary

Creating a local commit is reversible and does not change staging. Pushing the
candidate triggers GitHub Actions and Render `checksPass` auto-deploy behavior,
so the push is held for explicit Product Owner approval.

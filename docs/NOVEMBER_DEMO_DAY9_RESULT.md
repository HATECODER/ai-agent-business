# November demo Day 9 result

Date: 2026-10-12
Status: implemented locally; awaiting Product Owner approval

## What changed

- Added a protected, tenant-scoped `POST /api/v1/copilot/query` API.
- Added bounded routing for restock, finance, inactive-customer and task
  questions in English, Bangla and Banglish.
- Added a merchant Copilot page at `/copilot`, linked from Inventory.
- Every answer shows source facts, the fixed demo reference date and material
  limitations. Missing rows produce an explicit zero/unavailable-style answer.
- The API rechecks `copilot.use` and the relevant domain permission before a
  business reader reaches PostgreSQL.
- The staging Copilot uses deterministic mode for the zero-cost student demo.
  It does not mix in SQLite facts and does not send tenant data to an external
  model. A reviewed model explanation adapter can be enabled later without
  moving arithmetic or authorization into the model.

## Safety boundaries

- Question length is limited to 500 characters at both BFF and API boundaries.
- The BFF requires the existing authenticated session and exact same-origin
  mutation check.
- Restock output is read-only; no purchase or inventory write is exposed.
- Customer output contains pseudonymous keys only.
- Source failures return sanitized errors.

## Verification

- Backend Copilot unit and API tests cover classification, exact fixture totals,
  missing rows, permission denial and request bounds.
- Frontend type checking, unit tests and production build cover the new page and
  BFF route.
- Repository `run.ps1 -CheckOnly`, Ruff and Bandit results are recorded after
  the full Day 9 verification run.

## Deferred to Day 10+

- A structured restock review proposal with suggested quantities and explicit
  review state.
- Optional model wording/translation after provider terms, data fields and the
  spending cap are reviewed. Deterministic source facts remain authoritative.
- Deployment and live browser verification wait for the later candidate phase.

# November demo Day 10 result

Date: 2026-10-12
Status: implemented locally; awaiting Product Owner approval

## What changed

- Added a fifth supported Copilot request: `Prepare a restock review proposal`.
- Added structured proposal rows showing SKU, product/variant, location, current
  quantity, low-stock level, suggested quantity, source and observation time.
- Applied the Day 1 approved formula in Python:
  `max(0, (2 * low_stock_threshold) - current_quantity)`.
- Added a visible `Review only` state and an explicit statement that no external
  action occurred.
- Retained the visible deterministic/offline mode so the student-funded demo
  works without an external model or model charge.

## Safety boundaries

- Inventory facts still come from the authorized tenant reader.
- The model does not calculate quantities.
- There is no approve, execute, purchase or inventory-write control or endpoint.
- Missing low-stock rows return an empty factual answer, not an invented plan.
- React renders returned strings as text; raw HTML rendering is prohibited by a
  source-level regression test.

## Verification

- Copilot tests verify the exact suggested quantity and review-only state.
- Frontend tests verify the visible non-execution wording and absence of raw HTML
  or execution controls.
- Full repository, frontend type/build and targeted static checks are recorded
  after the final Day 10 verification run.

## Deferred

- Any approval or execution workflow.
- Supplier integration, purchase-order creation and inventory mutation.
- External model wording/translation and associated provider cost.
- Staging deployment and live browser rehearsal remain later schedule steps.

# November demo Day 14 result

Date: 2026-10-12
Status: approved 2026-10-12

## What changed

- Added a repeatable authenticated browser rehearsal covering Inventory and all
  five approved Copilot questions.
- Added phone (390x844), tablet (820x1180) and desktop (1440x900) width checks.
- Changed authentication capture to use the actual browser-window dimensions.
- Prevented the capture helper from forcing an operator from Copilot back to
  Inventory during its readiness loop.
- Increased the BFF upstream timeout from 8 to 65 seconds for Render free-tier
  cold starts.
- Added an operator guide with exact facts, timing, limits and recovery steps.

## Rehearsal result

The authenticated staging command completed **5/5 checks**:

- clean-browser walkthrough 1: passed;
- clean-browser walkthrough 2: passed;
- phone fit: passed;
- tablet fit: passed;
- desktop fit: passed.

Each walkthrough verified 12 inventory rows, the 5/2 stock summary, SKU search,
the attention filter, the disabled upload boundary, all five grounded answers,
the 39-unit proposal and the absence of an execution control.

Two local WebM walkthrough recordings were generated as fallback material.
They are ignored, machine-local artifacts and are not suitable for source
control or public sharing. The temporary encrypted authentication state was
removed after the successful rehearsal.

## Deployment evidence

- Application commit: `ed093f03895f29b3a3222405fb7bef626015b642`
- GitHub Actions run: `38235166445`, completed successfully
- Staging Inventory and Copilot routes returned HTTP 200 after the push

## Known limits

- Render free services may need up to about one minute to wake.
- Live CSV preview remains disabled until private malware scanning is funded.
- Demo data is synthetic and fixed to 1 November 2026.
- Copilot is deterministic and supports the five rehearsed question families.
- Restock output is review-only; there is no purchase or inventory mutation.

## Approval boundary

The Product Owner approved the Day 14 rehearsal evidence and wording on
2026-10-12. Day 15 fixes only confirmed blockers, records final acceptance and
freezes the candidate.

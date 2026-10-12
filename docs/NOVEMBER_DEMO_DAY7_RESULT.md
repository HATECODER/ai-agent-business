# November Demo Day 7 Result

Date: 2026-10-12
State: Awaiting Product Owner approval

## UI changes

- The source banner now shows the latest valid inventory observation time in
  the established Asia/Dhaka display format.
- When no valid observation exists, the source banner says that no observation
  time is available instead of presenting stale certainty.
- The zero-cost deployment explicitly disables the CSV file control and labels
  the action `Preview unavailable`.
- A visible explanation tells the merchant that private malware scanning is the
  dependency and that offline classification evidence is available.
- Mobile spacing and full-width actions were tightened at 560 px and below.
- Existing signed-out, membership-denied, service-unavailable and role-denied
  states remain fail closed.

## Verification

- Unit tests cover latest-observation selection and invalid timestamps.
- Browser security checks cover the disabled preview state and page-level
  horizontal overflow at a 390 x 844 mobile viewport.
- TypeScript type checking and the production build must pass before approval.

## Deployment boundary

This checkpoint prepares the UI change locally. It does not deploy, change
authentication, enable uploads or create a paid service.

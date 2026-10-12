# November merchant prototype acceptance record

Recorded: 2026-10-12 (Asia/Dhaka)
Dataset: `november-v1`
Reference date: 2026-11-01
Deployed application baseline: `ed093f03895f29b3a3222405fb7bef626015b642`
Product Owner: repository owner
Independent human reviewer: assign before the T-5 checkpoint

## Acceptance matrix

| Requirement | Result | Evidence |
|---|---|---|
| Account is limited to the configured workspace | Pass | Phase 1H wrong-workspace, membership and session-revocation evidence |
| Inventory matches the fixture | Pass | 12 variants, 5 low stock and 2 out of stock in both Day 14 walkthroughs |
| Offline CSV classifications are correct | Pass | Day 6 new/changed/error/conflict tests |
| Deployed upload remains unavailable | Pass | Disabled control and explanatory notice verified in both walkthroughs |
| Dormant malware scanner failure behavior is covered | Pass | Day 4-5 scanner adapter and cleanup tests |
| Funded live-upload controls are tracked | Pass with deferral | Private scanner hosting, live rate limits and enabled-path checks remain outside the zero-cost scope |
| Five questions work in three language forms | Pass | Day 11 evaluation: 15/15 |
| Missing/failure behavior is safe and deterministic mode is labeled | Pass | Day 9 and Day 12 tests plus visible Day 14 mode label |
| Restock proposal contains evidence and cannot execute | Pass | Seven review lines, 39 units, no approval/order/write control |
| Responsive and failure states are usable | Pass | 390x844, 820x1180 and 1440x900 browser checks |
| Secrets and private IDs are excluded from normal UI/evidence | Pass | Security tests and tracked-file review; temporary auth state removed after rehearsal |
| Candidate CI, recovery and rollback evidence exist | Pass | GitHub run `38235166445` and `NOVEMBER_DEMO_RECOVERY.md` |
| Two clean-browser rehearsals and fallback material exist | Pass | Day 14 5/5 run and two ignored local WebM recordings |
| Product Owner readiness | Pass | Day 15 push and freeze approved 2026-10-12 |
| Independent teammate review | Scheduled | Assign a teammate and complete the T-5 read-through before the meeting |

## Accepted demonstration boundary

The candidate demonstrates authenticated inventory visibility, search and
attention filtering; five grounded business questions; and a review-only
restock proposal. Data is synthetic and fixed to 1 November 2026. No inventory
apply, purchase, supplier message, campaign execution or external action is
available.

CSV upload remains visibly disabled because the student-funded environment has
no private malware scanner. Offline parser and scanner-adapter tests demonstrate
the future activation path without claiming that live upload is complete.

## Known limitations

1. Render free services may need up to about 65 seconds to wake.
2. The dedicated staging account, Auth0, Redis session store and Supabase
   project must be available for the live path.
3. Copilot uses deterministic templates and supports five question families.
4. Fixture totals are a demonstration snapshot rather than live merchant data.
5. Local fallback recordings show an authenticated staging session. Keep them
   on the operator device and do not commit or publish them.
6. Production launch still requires funded malware scanning, managed database
   backup/restore, monitoring, support ownership and a separate security review.

## Freeze rule

After the 2026-10-12 Day 15 approval, accept only meeting-blocking fixes. For any fix, rerun
the affected tests and both walkthroughs, record the new commit, and obtain a
fresh Product Owner decision. Do not enable deferred features inside the frozen
November candidate.

## Remaining human checkpoints

- Assign the independent teammate reviewer by T-5.
- Have that reviewer compare the operator script with the visible staging flow.
- Confirm the meeting date, presentation device, network and backup connection.
- Warm both Render services 30 minutes before the meeting.

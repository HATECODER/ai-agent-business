# November merchant demo operator guide

Prepared: 2026-10-12 (Asia/Dhaka)

## Before the meeting

1. Use a supported desktop browser and a stable connection.
2. Open `https://bizpilot-hatecoder-staging-web.onrender.com/inventory` about
   five minutes early so the free Render services can wake.
3. Sign in with the dedicated staging merchant account.
4. Confirm Inventory shows 12 variants, 5 low-stock variants and 2 out-of-stock
   variants. Do not continue if the secure-session warning remains after one
   minute and one refresh.
5. Keep the two local fallback recordings available. They live under the
   ignored `apps/web/test-results/november-demo-rehearsal-clean-browser-*`
   folders after `npm run browser:demo:rehearse` and must not be committed or
   shared because they depict an authenticated staging session.

## Ten-minute walkthrough

| Time | Operator action | Fact to state |
|---|---|---|
| 0:00-1:00 | Open Inventory and identify the active staging workspace | Synthetic fixture data is dated 1 November 2026 |
| 1:00-2:30 | Search `BP-KUR-BLU-M`, clear search, then enable **Needs attention** | 12 variants; 5 low stock; 2 out of stock |
| 2:30-3:00 | Show the disabled CSV preview notice | Upload remains disabled until private malware scanning is funded |
| 3:00-3:45 | Ask **Which products need restocking?** | 7 variants meet the approved attention rule |
| 3:45-4:30 | Ask **Show today's financial summary.** | BDT 5,000 revenue; BDT 3,500 received; BDT 1,500 receivable; BDT 800 expenses |
| 4:30-5:15 | Ask **Which customers have been inactive?** | `CUST-002`, `CUST-004`, `CUST-005`; no personal details shown |
| 5:15-6:00 | Ask **What tasks need attention?** | 4 pending or in-progress tasks |
| 6:00-8:00 | Ask **Prepare a restock review proposal.** | 7 lines totaling 39 units, calculated from source facts |
| 8:00-9:00 | Point to **Review only** | No purchase, message or inventory change occurred |
| 9:00-10:00 | Explain current limits and ask for feedback | Prototype supports this fixed workflow and synthetic data |

## Recovery during the demo

- If a free service is waking, wait up to 65 seconds and refresh once.
- If sign-in is unavailable, play a local fallback walkthrough and label it as
  a recording of the staging prototype.
- If facts differ from the values above, stop the data portion rather than
  improvising an answer.
- Do not enable CSV upload, create an order or promise an execution workflow.

## Repeat the rehearsal

From `apps/web`, set `BIZPILOT_BROWSER_BASE_URL` to the exact staging origin,
capture a fresh session once, and run:

```powershell
npm.cmd run browser:demo:rehearse
```

The command runs two isolated walkthroughs plus phone, tablet and desktop fit
checks. Authentication state and recordings remain ignored local artifacts.

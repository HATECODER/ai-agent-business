# BizPilot AI — One-Week Merchant Demonstration Plan

## Purpose

This plan creates a reliable, understandable merchant demonstration in one
week. It is a focused vertical slice, not a claim that the complete commercial
SaaS product is finished.

Implementation starts only after **Phase 1H: Auth0 staging and real-browser
security validation** is completed and reviewed.

## Demonstration scope

The demo will show one complete workflow for one merchant workspace:

1. Merchant signs in with the managed Auth0 session.
2. Merchant views inventory by product, variant, SKU, location, quantity and
   stock status.
3. Merchant uploads one sanitized CSV export from the existing system.
4. BizPilot validates and previews the changes.
5. Merchant identifies low-stock products.
6. Merchant asks the AI Copilot questions using local business data.
7. BizPilot creates a restock or campaign proposal.
8. Merchant reviews the proposal; no external action executes automatically.

### Supported demo questions

- Which products need restocking?
- Show today's financial summary.
- Which customers have been inactive?
- What tasks need attention?
- Prepare a restock review proposal.

Business numbers come from deterministic backend tools. Gemini is used only for
language, explanation and bounded recommendations. Offline mode remains the
fallback when provider access is unavailable.

## Source and data boundary

- First merchant source: one CSV export.
- One staging workspace and one approved merchant account.
- Use a sanitized sample or data explicitly approved for the demonstration.
- Do not collect provider credentials, payment credentials or unnecessary
  customer personal data.
- Keep CSV import preview-only. No stock, payment, message or external system
  write is enabled in this week.

## Daily plan

### Day 1 — Scope and data freeze

- Confirm the exact demo workflow and five questions.
- Obtain a sanitized merchant CSV and validate its columns.
- Prepare 10–30 representative products plus a small customer/order sample.
- Confirm metric definitions, timezone and currency with the merchant.
- Create one staging workspace and record the demo acceptance checklist.

**Exit:** the sample data loads deterministically and the walkthrough has no
undefined business terms.

### Day 2 — Staging access

- Configure Auth0 staging application, callback and logout URLs.
- Configure the Next.js BFF, FastAPI API and PostgreSQL connection.
- Enable HTTPS and server-only secrets.
- Verify sign-in, sign-out, workspace membership and denied access.
- Keep the application fail-closed if any required configuration is absent.

**Fallback:** if Auth0 setup is blocked, use the existing protected Streamlit
pilot for the demonstration. Do not add a temporary insecure login bypass.

**Exit:** a clean browser can sign in and reach the intended workspace.

### Day 3 — Merchant workflow

- Test CSV upload and preview with valid, duplicate, stale and invalid rows.
- Configure the reviewed staging malware scanner.
- Verify low-stock and summary calculations against known values.
- Confirm preview never changes inventory.
- Verify clear empty, error and permission states.
- Confirm internal IDs, bearer tokens and secrets never reach the browser.

**Exit:** the complete inventory flow works twice from a clean browser.

### Day 4 — Copilot demonstration

- Connect the approved Gemini model and keep offline mode available.
- Test the five supported questions in English, Bangla and Banglish where
  applicable.
- Verify every financial and inventory number against deterministic tools.
- Test provider failure and confirm the UI gives a safe, understandable error.
- Keep proposals review-only and show their evidence/source context.

**Exit:** every supported question has a reviewed expected answer or a clear
handoff/refusal.

### Day 5 — Polish and rehearsal

- Fix demo-blocking defects only.
- Test desktop and mobile widths.
- Verify session expiry, logout and refresh behavior.
- Create a database backup and verify restore instructions.
- Rehearse a ten-minute walkthrough from a clean browser.
- Prepare a short backup recording or screenshots.

**Exit:** the demo can be repeated without developer intervention.

### Day 6–7 — Buffer and demonstration

Reserve the final time for deployment recovery, data corrections, network/API
issues, one final rehearsal and the merchant meeting. Do not add new features
in the buffer.

## Explicitly deferred

- The 18-agent catalogue
- Live Shopify, WooCommerce or POS synchronization
- Automatic inventory adjustments
- Payments, refunds, invoices or customer messaging
- Billing and platform-admin console
- Multi-workspace switching
- Advanced RAG and fine-tuning
- Full production monitoring and incident operations
- Production inventory apply workflow

## Demo acceptance criteria

The prototype is ready when:

- the merchant can sign in;
- inventory loads from the approved source;
- CSV preview shows valid, changed, conflict and error results;
- low-stock calculations match the known sample;
- Copilot answers use the local data and do not invent business numbers;
- proposals require human review;
- no stock, payment or external communication action executes automatically;
- offline mode still demonstrates the core flow;
- the walkthrough succeeds from a clean browser twice.

## Architecture used for this demonstration

```text
Merchant CSV
    ↓
Next.js merchant UI
    ↓
Auth0 managed session
    ↓
Server-side BFF
    ↓
FastAPI authorization and deterministic tools
    ↓
PostgreSQL tenant data
    ↓
AI Copilot for explanation and bounded proposals
```

## Time and risk statement

The existing Phase 1G foundation makes this demonstration achievable in one
week if the merchant sample data and Auth0 credentials are available on Day 1.
The largest risks are delayed identity-provider setup, unclear source data,
malware-scanner configuration and unavailable model/network access. Offline
mode and the protected Streamlit pilot are the planned fallbacks.

This plan produces a **workable merchant demonstration**, not a production
release. Production readiness still requires connectors, durable writes,
monitoring, recovery drills, privacy operations and a controlled pilot.

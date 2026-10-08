# Decision 0002: Commercial R1 Foundation

Date: 2026-10-08

## Status

Accepted by the Project Owner on 2026-10-08. This decision supersedes ambiguous use of the word `vendor` for a BizPilot customer and formalizes the first commercial implementation boundary.

## Context

The current repository is a single-workspace Streamlit/SQLite evaluation pilot with fictional data. Commercial R1 needs a clear identity model, a small role set, a first real merchant-data path, and security boundaries before production code or real customer data is introduced.

There is not yet verified evidence that the first target merchants use the same commerce platform. Choosing a Shopify or WooCommerce connector before merchant validation could spend several weeks on the wrong integration. CSV is broadly available, cheap to validate, and can establish the product/variant/location data contract. It is manual and cannot be presented as real-time sync.

Official platform documentation confirms that later connectors have meaningful operational requirements:

- [Shopify webhooks](https://shopify.dev/docs/apps/build/webhooks) require signature verification, duplicate handling, event-time ordering, and reconciliation because delivery alone is not guaranteed.
- [WooCommerce REST authentication](https://developer.woocommerce.com/docs/apis/rest-api/authentication) uses store-issued keys tied to WordPress user capabilities, and its [webhooks](https://developer.woocommerce.com/docs/apis/rest-api/v3/webhooks/) carry HMAC signatures and can be disabled after repeated failures.
- [Shopify inventory CSV](https://help.shopify.com/en/manual/products/inventory/setup/inventory-csv) uses current/new quantity comparison to reduce accidental overwrites; R1 adopts the same conflict-protection principle without copying its file format.

## Decision

### 1. Canonical terminology

| Term | Canonical meaning |
|---|---|
| Platform operator | The company operating BizPilot. |
| Platform user | An employee/contractor authorized to operate or support BizPilot. |
| Platform Admin | A high-trust platform user. Never a merchant role. |
| Merchant / tenant | One customer business with an isolated BizPilot workspace. |
| Merchant user | A person with a verified membership in a merchant workspace. |
| Merchant Owner | The single accountable tenant role for ownership, billing, privileged access, and high-risk approvals. |
| Merchant Admin | A tenant administrator without ownership transfer or platform billing authority. |
| Supplier / vendor | A business supplying goods/services to a merchant. `Vendor` does not mean a BizPilot customer. |
| End customer | A shopper/customer of a merchant. This identity cannot access merchant or platform administration. |
| Actor | The authenticated user/service plus active tenant, role, permissions, and request/session context. |
| Active tenant | The one explicitly selected merchant workspace for the current request/tab. |
| Connection | A tenant-authorized external source/channel integration. |
| Source of truth | The system contractually/operationally authoritative for a particular field or event. |
| Projection | A BizPilot copy derived from another source, including source identity, version, and freshness. |
| Proposal | A validated, nonexecuted description of a possible action. |
| Approval | Permission for one exact proposal payload under current actor/policy/source state. |

URLs, database names, logs, metrics, and code use `tenant` as the technical term. Merchant-facing UI uses `Business` or `Workspace` where that is easier to understand.

### 2. R1 role presets

R1 uses fixed roles: Merchant Owner, Merchant Admin, Operations, Growth, Finance Viewer, and Viewer. Custom roles are deferred. Platform roles remain separate: Platform Owner, Platform Operator, Support Agent, and Security Responder.

The detailed permission contract is [R1_ROLE_PERMISSION_MATRIX.md](../R1_ROLE_PERMISSION_MATRIX.md). Backend permissions are authoritative; hiding a button is not authorization.

Finance Viewer is included because read-only financial access is a common small-business responsibility and is materially safer than giving broad Admin access. It has no refund, payout, credential, customer-export, team, or campaign permission.

### 3. First merchant source

The first R1 merchant source is a **staged UTF-8 CSV inventory snapshot**.

Initial accepted data:

- product name;
- variant name/options;
- tenant-scoped SKU;
- location code/name;
- counted quantity;
- low-stock threshold;
- optional base price in BDT;
- optional expected record version for conflict detection.

Initial excluded data:

- customer names, email addresses, phone numbers, or addresses;
- orders, payments, bank details, employee/HR data;
- formulas, macros, images, arbitrary HTML, or executable content;
- tenant IDs, internal database IDs, role/permission fields, or secrets.

The merchant's existing spreadsheet/POS/commerce system remains the external source of truth. BizPilot stores an attributable projection and local inventory-movement ledger. Every screen shows `CSV snapshot`, uploader, import time, and freshness. A later import cannot silently overwrite a record changed since its expected version.

Initial safety bounds are 5 MB and 10,000 rows per file, subject to representative load testing. R1 accepts CSV only; XLSX is deferred until its parser and file-security controls are separately gated.

Required flow:

```text
Upload to quarantine
  â†’ validate file/type/size/encoding/headers/rows
  â†’ match by tenant-scoped SKU + location
  â†’ show new/change/conflict/error/unchanged preview
  â†’ authorized user applies the exact batch
  â†’ background job writes movements transactionally and idempotently
  â†’ results, error file, freshness, and audit become visible
```

The file feature stays disabled until `SEC-INP-005` through `SEC-INP-007` and `SEC-ACT-006` in [SECURITY_REQUIREMENTS.md](../../SECURITY_REQUIREMENTS.md) pass.

### 4. First API connector decision gate

Shopify GraphQL Admin API/webhooks is the reference connector candidate because its current official documentation provides scoped authentication, event metadata, HMAC verification, deduplication IDs, and reconciliation guidance. It is not yet a committed build target.

Before connector implementation, Phase 0 discovery must obtain:

1. at least three target-merchant interviews;
2. a count of Shopify, WooCommerce, POS, spreadsheet, and custom systems;
3. one signed pilot merchant for the selected connector;
4. a sanitized representative export/API sample;
5. confirmed read scopes, API access, webhook support, source ownership, and deletion/uninstall behavior;
6. a written decision to select Shopify, select WooCommerce, or remain CSV-first for the controlled pilot.

If no connector has a signed pilot merchant, connector work does not start. CSV remains clearly labelled manual/stale-prone and no real-time claim is made.

### 5. Initial source-of-truth ownership

| Domain/field | R1 owner | BizPilot behavior |
|---|---|---|
| Products, variants, SKU | Merchant's stated source | Imported projection; local edit is an explicit override with audit |
| Physical stock count | Merchant's stated source/physical count | Snapshot plus local movements; show freshness and conflicts |
| Low-stock threshold | BizPilot tenant configuration | Authorized local edit with audit |
| Internal tasks | BizPilot | Transactional system of record |
| Proposals/approvals/executions | BizPilot | Immutable state transitions and audit |
| Users/memberships/permissions | Managed identity + BizPilot membership policy | Identity provider authenticates; BizPilot authorizes |
| AI response | No system-of-record authority | Explanation/recommendation linked to deterministic evidence |
| Orders/payments/customers | Out of first source scope | Feature disabled for real data until a connector/domain gate passes |

## Consequences

### Benefits

- Product, tenant, and role contracts can be implemented without waiting for a third-party app review.
- The first real-data surface is smaller and excludes customer PII.
- Merchant UX, import correctness, conflict handling, and audit can be validated early.
- Connector choice follows customer evidence instead of assumption.

### Costs and limitations

- CSV is not real-time and requires merchant effort.
- Inventory can become stale between imports.
- Secure upload/import processing must be built before real files are accepted.
- Finance, customer growth, and order workflows remain synthetic/disabled for real data until their source contracts are approved.

## Phase 0 exit criteria

- Product Owner approves this decision or records exact amendments.
- Role matrix has no unresolved permission ambiguity for R1 features.
- Threat model owners and release-blocking risks are accepted.
- Three merchant interviews and one representative sanitized file are available before accepting the source decision as market-validated.
- No real merchant file is uploaded to the current Streamlit/SQLite prototype.

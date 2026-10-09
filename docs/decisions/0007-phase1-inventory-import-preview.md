# Decision 0007: Phase 1 Inventory Import Preview Boundary

Date: 2026-10-09

## Status

Accepted by the Product Owner on 2026-10-09. Inventory apply remains disabled.

## Implemented boundary

- `POST /api/v1/inventory/imports/preview` accepts one staged CSV only from an
  authenticated Owner, Admin, or Operations member with `inventory.import`.
- Files must be `.csv`, use an allowlisted CSV content type, be valid UTF-8,
  contain no NUL bytes, stay within 5 MB, and contain at most 10,000 data rows.
- The header contract is exact. Unknown, duplicate, and missing headers are
  rejected before any metadata is stored.
- Text, integer, BDT decimal, JSON options, and optional record-version fields
  are normalized and bounded by deterministic Python code.
- Text fields beginning with spreadsheet formula markers are rejected. Error
  CSVs contain controlled row/code/message fields and never echo merchant cell
  values, preventing formula injection through the report.
- A configured malware scanner must approve the in-memory bytes before parsing.
  The default application has no permissive scanner and returns a sanitized
  `503` until a reviewed deployment adapter is injected.
- Raw CSV bytes are discarded after the request. They are never written to the
  database, object storage, logs, error reports, or a model.
- PostgreSQL stores only a SHA-256 digest, sanitized filename, actor membership,
  bounded counts, status, creation time, and 24-hour expiry, plus up to 200
  controlled validation errors.
- Preview rows are deterministically classified as new, changed, conflicting,
  or unchanged against the current tenant inventory. A supplied stale
  `expected_record_version` is a conflict.
- The two preview tables use forced RLS and composite tenant relationships.
  Runtime receives only `SELECT` and `INSERT` on them. It cannot update/delete
  preview metadata or write any product, variant, location, balance, or movement.
- `GET /api/v1/inventory/imports/{preview_id}/errors.csv` requires the same
  permission, tenant scopes the lookup through RLS, rejects expired previews,
  and uses a fixed safe download filename.
- Every response states `apply_enabled: false`. No apply endpoint exists.

## CSV contract

Required columns:

- `product_name`
- `variant_name`
- `sku`
- `location_code`
- `location_name`
- `quantity`
- `low_stock_threshold`

Optional columns:

- `variant_options`: a JSON object with at most 20 text key/value entries
- `base_price_bdt`: a non-negative BDT amount with at most two decimals
- `expected_record_version`: a positive integer used for conflict detection

`sku + location_code` must be unique inside one file. The template is
[`inventory-import-template.csv`](../templates/inventory-import-template.csv).

## Security review

This adds an endpoint, dependency declaration, and upload path, so
`SEC-BLD-017` and `SEC-BLD-018` require the new negative tests and this record.
The boundary addresses the application-level parts of `SEC-INP-005` through
`SEC-INP-007` and `SEC-ACT-006`, but the complete upload feature remains off.

The following remain deployment blockers:

- choose and review a local/private malware scanning adapter and prove failure,
  timeout, signature-update, and malicious-file behavior;
- configure reverse-proxy request-body and endpoint rate limits so oversized
  multipart bodies are rejected before application parsing;
- add a privileged scheduled purge for expired metadata and prove deletion;
- add private object storage, tenant-scoped signed downloads, and quarantine if
  a later workflow needs to retain raw files;
- add a staged apply proposal with conflict resolution, exact confirmation,
  authorization recheck, idempotency, movement ledger entries, and audit.

No exception is claimed for these items. The import apply capability remains
disabled until its separate checkpoint is accepted.

## Verification contract

- unauthorized roles cannot invoke preview or download errors;
- missing scanner/configuration fails closed without parsing or storing data;
- unsafe extension, MIME, encoding, size, headers, row count, types, formulas,
  duplicate keys, and versions are rejected deterministically;
- scanner rejection happens before parsing and persistence;
- two tenants cannot read each other's preview or error metadata;
- runtime cannot forge another tenant or update/delete preview metadata;
- preview creates no product, variant, location, balance, or movement rows;
- migration upgrade/downgrade and RLS checks run against PostgreSQL in CI.

## Local verification evidence

On 2026-10-09, the complete BUILD security gate passed 129 deterministic tests,
the secret and policy checks, Ruff, Bandit, the locked dependency audit, and the
bounded load check. A separate disposable container using the same pinned
PostgreSQL 17.6 image as CI passed all 11 migration/RLS integration tests. The
container was removed after the run. No live AI provider or merchant data was
used.

## Next checkpoint

After Product Owner approval, implement the merchant-facing inventory management
experience around the read API and preview contract, or approve the separate
import-apply design. Production enablement still requires the deployment
blockers above.

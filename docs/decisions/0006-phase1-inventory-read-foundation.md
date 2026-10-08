# Decision 0006: Phase 1 Tenant Inventory Read Foundation

Date: 2026-10-08

## Status

Implemented; pending Product Owner checkpoint review.

## Implemented boundary

- PostgreSQL now stores tenant-owned products, variants, inventory balances,
  and an inventory movement ledger foundation.
- Tenant-scoped SKU uniqueness and composite tenant foreign keys prevent a
  variant, location, balance, or movement from linking records across tenants.
- Prices use integer minor units plus a three-letter currency. Quantities,
  thresholds, record versions, and movement arithmetic have database checks.
- CSV-derived records require an attributable source reference. Inventory
  balances expose source kind, source version, observation time, and record
  version so callers can display freshness and detect future write conflicts.
- Product, variant, balance, and movement tables use forced, default-deny RLS.
- `bizpilot_runtime` receives `SELECT` only for the inventory domain. Phase 1D
  also revokes its earlier location write grants.
- The protected `GET /api/v1/inventory` endpoint requires the existing
  `inventory.read` permission and a current Phase 1C tenant authority.
- The endpoint limits pages to 100 records, validates an optional UUID cursor,
  supports a low-stock filter, and uses tenant-scoped keyset pagination.
- Finance Viewer is denied. Owner, Admin, Operations, Growth, and Viewer follow
  the accepted R1 permission matrix.
- Query failures return a generic `503` and sanitized security telemetry.

## Security and data constraints

The merchant source remains an external source of truth. `csv_snapshot` means a
dated projection, not live inventory. The response includes `observed_at` and
source metadata so the UI can state that clearly.

The movement table is not writable in this checkpoint. Its schema binds a human
actor through a tenant-scoped membership or identifies a system actor, records
before/delta/after values, reason, source, time, and a tenant idempotency key.

## Verification contract

- two tenants cannot read each other's product, variant, balance, or movement;
- runtime cannot insert inventory-domain or location records;
- composite keys reject cross-tenant relationships even under migration-owner
  access;
- low-stock calculation is deterministic SQL over quantity and threshold;
- pagination returns stable bounded pages without exposing another tenant;
- source, price, currency, quantity, threshold, and record version serialize
  exactly;
- every allowed read role reaches the API and Finance Viewer is denied;
- migration upgrade/downgrade and all RLS assertions run on real PostgreSQL.

## Current limitations

- No upload, CSV parser, quarantine, staging, preview, conflict resolution, or
  apply workflow is enabled.
- No inventory adjustment or movement write API is enabled.
- No merchant-facing inventory management UI is included in the commercial
  backend yet.
- No connector or real merchant dataset has been selected or loaded.
- Location filtering and text search are deferred until representative merchant
  data establishes their actual query and indexing needs.

## Verification evidence

On 2026-10-08, the complete local BUILD security gate ran with the pinned
PostgreSQL 17.6 image and passed all 128 tests without skips. The nine database
tests applied and rolled back all three migrations and verified cross-tenant
RLS, composite-key rejection, runtime read-only privileges, source evidence,
low-stock filtering, and keyset pagination. Secret scanning, Ruff, Bandit,
locked-dependency audit, and the bounded load check also passed. The disposable
database container was removed.

## Next checkpoint

Build the staged CSV validation and preview boundary without applying data:
strict UTF-8 CSV parsing, file/row/header limits, tenant-isolated quarantine
metadata, normalized row validation, formula-safe error export, and a preview
summary. Keep apply/import writes disabled until that checkpoint is reviewed.

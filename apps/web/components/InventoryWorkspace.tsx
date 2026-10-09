"use client";

import { useMemo, useState } from "react";

import {
  filterInventory,
  formatObservedAt,
  hasPermission,
  inventoryStatus,
  inventorySummary,
  type InventoryItem,
  type InventoryStatus,
} from "@/lib/inventory";

interface InventoryWorkspaceProps {
  workspaceName: string;
  roleLabel: string;
  permissions: string[];
  items: InventoryItem[];
  connectionReady: boolean;
}

const statusLabel: Record<InventoryStatus, string> = {
  in_stock: "In stock",
  low_stock: "Low stock",
  out_of_stock: "Out of stock",
};

export function InventoryWorkspace({
  workspaceName,
  roleLabel,
  permissions,
  items,
  connectionReady,
}: InventoryWorkspaceProps) {
  const [query, setQuery] = useState("");
  const [lowStockOnly, setLowStockOnly] = useState(false);
  const summary = useMemo(() => inventorySummary(items), [items]);
  const visibleItems = useMemo(
    () => filterInventory(items, query, lowStockOnly),
    [items, query, lowStockOnly],
  );
  const canImport = hasPermission(permissions, "inventory.import");

  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Main navigation">
        <a className="brand" href="/inventory" aria-label="BizPilot home">
          <span className="brand-mark">B</span>
          <span>BizPilot</span>
        </a>
        <nav>
          <a className="nav-link active" href="/inventory" aria-current="page">
            <span aria-hidden="true">▦</span> Inventory
          </a>
          <span className="nav-link disabled"><span aria-hidden="true">✓</span> Tasks</span>
          <span className="nav-link disabled"><span aria-hidden="true">◎</span> Growth</span>
          <span className="nav-link disabled"><span aria-hidden="true">৳</span> Finance</span>
        </nav>
        <div className="workspace-card">
          <span className="eyebrow">Active workspace</span>
          <strong>{workspaceName}</strong>
          <span>{roleLabel}</span>
        </div>
      </aside>

      <main className="main-content">
        <header className="page-header">
          <div>
            <span className="eyebrow">Operations</span>
            <h1>Inventory</h1>
            <p>See stock by product, variant, and location without database IDs.</p>
          </div>
          <a className="secondary-button" href="/inventory-import-template.csv" download>
            Download CSV template
          </a>
        </header>

        {!connectionReady && (
          <section className="notice warning" role="status">
            <strong>Secure merchant session required</strong>
            <span>
              The interface is ready, but live inventory and upload controls stay disabled until
              the managed browser session adapter is connected.
            </span>
          </section>
        )}

        <section className="source-banner" aria-label="Inventory source information">
          <div>
            <span className="source-dot" aria-hidden="true" />
            <strong>CSV snapshot</strong>
          </div>
          <p>Manual source · always check “Last updated” before making a stock decision.</p>
        </section>

        <section className="metric-grid" aria-label="Inventory summary">
          <article className="metric-card"><span>Variants</span><strong>{summary.total}</strong></article>
          <article className="metric-card"><span>Low stock</span><strong>{summary.lowStock}</strong></article>
          <article className="metric-card"><span>Out of stock</span><strong>{summary.outOfStock}</strong></article>
        </section>

        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Stock list</h2>
              <p>Search by product, variant, SKU, or location.</p>
            </div>
            <div className="filters">
              <label className="search-field">
                <span className="sr-only">Search inventory</span>
                <input
                  type="search"
                  placeholder="Search inventory"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                />
              </label>
              <label className="check-filter">
                <input
                  type="checkbox"
                  checked={lowStockOnly}
                  onChange={(event) => setLowStockOnly(event.target.checked)}
                />
                Needs attention
              </label>
            </div>
          </div>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Product</th><th>Variant</th><th>SKU</th><th>Location</th>
                  <th className="number">In stock</th><th className="number">Low-stock level</th>
                  <th>Status</th><th>Last updated</th>
                </tr>
              </thead>
              <tbody>
                {visibleItems.map((item) => {
                  const status = inventoryStatus(item);
                  return (
                    <tr key={item.inventory_id}>
                      <td><strong>{item.product_name}</strong></td>
                      <td>{item.variant_name}</td><td><code>{item.sku}</code></td>
                      <td>{item.location_name}</td><td className="number">{item.quantity}</td>
                      <td className="number">{item.low_stock_threshold}</td>
                      <td><span className={`status ${status}`}>{statusLabel[status]}</span></td>
                      <td>{formatObservedAt(item.observed_at)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {visibleItems.length === 0 && (
              <div className="empty-state">
                <span className="empty-icon" aria-hidden="true">□</span>
                <h3>{items.length ? "No matching stock" : "No inventory loaded"}</h3>
                <p>{items.length ? "Try a different search or remove the filter." : "Connect a secure merchant session to load this workspace."}</p>
              </div>
            )}
          </div>
        </section>

        <section className="import-panel">
          <div>
            <span className="eyebrow">Bulk update</span>
            <h2>Import inventory from CSV</h2>
            <p>Download the template, add up to 10,000 rows, then preview every change and error.</p>
          </div>
          <ol className="steps" aria-label="CSV import steps">
            <li><span>1</span><strong>Prepare</strong><small>UTF-8 CSV · 5 MB maximum</small></li>
            <li><span>2</span><strong>Preview</strong><small>New, changed, conflict, and error rows</small></li>
            <li><span>3</span><strong>Review</strong><small>No stock is changed in this phase</small></li>
          </ol>
          <button className="primary-button" type="button" disabled={!canImport || !connectionReady}>
            {!connectionReady
              ? "Connect secure session to import"
              : !canImport
                ? "Import not allowed for your role"
                : "Choose CSV to preview"}
          </button>
          <p className="helper-text">
            Preview only. Applying inventory changes is disabled and requires a later approval workflow.
          </p>
        </section>
      </main>
    </div>
  );
}

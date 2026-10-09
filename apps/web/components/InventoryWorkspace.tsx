"use client";

import { FormEvent, useMemo, useState } from "react";

import {
  filterInventory,
  formatObservedAt,
  hasPermission,
  inventoryStatus,
  inventorySummary,
  type InventoryItem,
  type InventoryStatus,
} from "@/lib/inventory";

type ConnectionState = "configuration" | "signed_out" | "denied" | "unavailable" | "ready";

interface InventoryWorkspaceProps {
  workspaceName: string;
  roleLabel: string;
  permissions: string[];
  items: InventoryItem[];
  connectionState: ConnectionState;
}

interface PreviewResult {
  preview_id: string;
  filename: string;
  expires_at: string;
  counts: {
    total: number;
    valid: number;
    errors: number;
    new: number;
    changes: number;
    conflicts: number;
    unchanged: number;
  };
  apply_enabled: false;
}

const statusLabel: Record<InventoryStatus, string> = {
  in_stock: "In stock",
  low_stock: "Low stock",
  out_of_stock: "Out of stock",
};

const connectionMessages: Record<ConnectionState, string> = {
  configuration: "Server setup is incomplete. An administrator must configure the managed identity and workspace settings.",
  signed_out: "Sign in with your managed business account to load this workspace.",
  denied: "Your account does not have an active membership for this workspace.",
  unavailable: "The secure session or inventory service is temporarily unavailable.",
  ready: "",
};

export function InventoryWorkspace({ workspaceName, roleLabel, permissions, items, connectionState }: InventoryWorkspaceProps) {
  const [query, setQuery] = useState("");
  const [lowStockOnly, setLowStockOnly] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<PreviewResult | null>(null);
  const [previewError, setPreviewError] = useState("");
  const [previewing, setPreviewing] = useState(false);
  const summary = useMemo(() => inventorySummary(items), [items]);
  const visibleItems = useMemo(() => filterInventory(items, query, lowStockOnly), [items, query, lowStockOnly]);
  const connectionReady = connectionState === "ready";
  const canImport = hasPermission(permissions, "inventory.import");

  async function submitPreview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedFile || !connectionReady || !canImport) return;
    setPreviewing(true);
    setPreview(null);
    setPreviewError("");
    const body = new FormData();
    body.set("file", selectedFile, selectedFile.name);
    try {
      const response = await fetch("/api/bff/inventory/imports/preview", {
        method: "POST",
        body,
        credentials: "same-origin",
      });
      const payload = (await response.json()) as PreviewResult | { detail?: string };
      if (!response.ok || !("counts" in payload)) {
        setPreviewError("detail" in payload && payload.detail ? payload.detail : "Preview could not be created.");
        return;
      }
      setPreview(payload);
    } catch {
      setPreviewError("Preview service is unavailable. Try again later.");
    } finally {
      setPreviewing(false);
    }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Main navigation">
        <a className="brand" href="/inventory" aria-label="BizPilot home"><span className="brand-mark">B</span><span>BizPilot</span></a>
        <nav>
          <a className="nav-link active" href="/inventory" aria-current="page"><span aria-hidden="true">I</span> Inventory</a>
          <span className="nav-link disabled"><span aria-hidden="true">T</span> Tasks</span>
          <span className="nav-link disabled"><span aria-hidden="true">G</span> Growth</span>
          <span className="nav-link disabled"><span aria-hidden="true">F</span> Finance</span>
        </nav>
        <div className="workspace-card"><span className="eyebrow">Active workspace</span><strong>{workspaceName}</strong><span>{roleLabel}</span></div>
      </aside>

      <main className="main-content">
        <header className="page-header">
          <div><span className="eyebrow">Operations</span><h1>Inventory</h1><p>See stock by product, variant, and location without database IDs.</p></div>
          <a className="secondary-button" href="/inventory-import-template.csv" download>Download CSV template</a>
          {connectionState === "signed_out" && <a className="primary-button" href="/auth/login">Sign in</a>}
          {connectionReady && <a className="secondary-button" href="/auth/logout">Sign out</a>}
        </header>

        {!connectionReady && <section className="notice warning" role="status"><strong>Secure merchant session required</strong><span>{connectionMessages[connectionState]}</span></section>}

        <section className="source-banner" aria-label="Inventory source information">
          <div><span className="source-dot" aria-hidden="true" /><strong>CSV snapshot</strong></div>
          <p>Manual source · always check “Last updated” before making a stock decision.</p>
        </section>

        <section className="metric-grid" aria-label="Inventory summary">
          <article className="metric-card"><span>Variants</span><strong>{summary.total}</strong></article>
          <article className="metric-card"><span>Low stock</span><strong>{summary.lowStock}</strong></article>
          <article className="metric-card"><span>Out of stock</span><strong>{summary.outOfStock}</strong></article>
        </section>

        <section className="panel">
          <div className="panel-heading">
            <div><h2>Stock list</h2><p>Search by product, variant, SKU, or location.</p></div>
            <div className="filters">
              <label className="search-field"><span className="sr-only">Search inventory</span><input type="search" placeholder="Search inventory" value={query} onChange={(event) => setQuery(event.target.value)} /></label>
              <label className="check-filter"><input type="checkbox" checked={lowStockOnly} onChange={(event) => setLowStockOnly(event.target.checked)} />Needs attention</label>
            </div>
          </div>

          <div className="table-wrap">
            <table>
              <thead><tr><th>Product</th><th>Variant</th><th>SKU</th><th>Location</th><th className="number">In stock</th><th className="number">Low-stock level</th><th>Status</th><th>Last updated</th></tr></thead>
              <tbody>{visibleItems.map((item) => {
                const status = inventoryStatus(item);
                return <tr key={`${item.sku}:${item.location_code}`}><td><strong>{item.product_name}</strong></td><td>{item.variant_name}</td><td><code>{item.sku}</code></td><td>{item.location_name}</td><td className="number">{item.quantity}</td><td className="number">{item.low_stock_threshold}</td><td><span className={`status ${status}`}>{statusLabel[status]}</span></td><td>{formatObservedAt(item.observed_at)}</td></tr>;
              })}</tbody>
            </table>
            {visibleItems.length === 0 && <div className="empty-state"><span className="empty-icon" aria-hidden="true">□</span><h3>{items.length ? "No matching stock" : "No inventory loaded"}</h3><p>{items.length ? "Try a different search or remove the filter." : connectionReady ? "This workspace has no inventory rows." : "Sign in to load this workspace."}</p></div>}
          </div>
        </section>

        <section className="import-panel">
          <div><span className="eyebrow">Bulk update</span><h2>Import inventory from CSV</h2><p>Download the template, add up to 10,000 rows, then preview every change and error.</p></div>
          <ol className="steps" aria-label="CSV import steps">
            <li><span>1</span><strong>Prepare</strong><small>UTF-8 CSV · 5 MB maximum</small></li>
            <li><span>2</span><strong>Preview</strong><small>New, changed, conflict, and error rows</small></li>
            <li><span>3</span><strong>Review</strong><small>No stock is changed in this phase</small></li>
          </ol>
          <form className="import-form" onSubmit={submitPreview}>
            <label className="file-field"><span>CSV file</span><input type="file" name="file" accept=".csv,text/csv,application/csv" disabled={!canImport || !connectionReady || previewing} onChange={(event) => { setSelectedFile(event.target.files?.[0] ?? null); setPreview(null); setPreviewError(""); }} /></label>
            <button className="primary-button" type="submit" disabled={!selectedFile || !canImport || !connectionReady || previewing}>{!connectionReady ? "Sign in to preview" : !canImport ? "Preview not allowed for your role" : previewing ? "Checking CSV…" : "Preview CSV"}</button>
          </form>
          {previewError && <div className="notice error" role="alert"><strong>Preview failed</strong><span>{previewError}</span></div>}
          {preview && <section className="preview-summary" aria-live="polite">
            <div><strong>Preview ready</strong><span>{preview.filename}</span></div>
            <dl><div><dt>Total</dt><dd>{preview.counts.total}</dd></div><div><dt>New</dt><dd>{preview.counts.new}</dd></div><div><dt>Changes</dt><dd>{preview.counts.changes}</dd></div><div><dt>Conflicts</dt><dd>{preview.counts.conflicts}</dd></div><div><dt>Errors</dt><dd>{preview.counts.errors}</dd></div></dl>
            <p>No inventory was changed. Applying this preview is not available.</p>
          </section>}
          <p className="helper-text">Preview only. Applying inventory changes is disabled and requires a later approval workflow.</p>
        </section>
      </main>
    </div>
  );
}

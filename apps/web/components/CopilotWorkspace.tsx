"use client";

import { FormEvent, useState } from "react";
import type { CopilotAnswer } from "@/lib/bff";

interface Props { workspaceName: string; roleLabel: string; ready: boolean; canUse: boolean; }

const prompts = [
  "Which products need restocking?",
  "Show today's financial summary.",
  "Which customers have been inactive?",
  "What tasks need attention?",
  "Prepare a restock review proposal.",
];

export function CopilotWorkspace({ workspaceName, roleLabel, ready, canUse }: Props) {
  const [message, setMessage] = useState(prompts[0]);
  const [result, setResult] = useState<CopilotAnswer | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function ask(event: FormEvent) {
    event.preventDefault();
    if (!ready || !canUse || message.trim().length < 2) return;
    setLoading(true); setError(""); setResult(null);
    try {
      const response = await fetch("/api/bff/copilot", { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message }) });
      const payload = await response.json() as CopilotAnswer | { detail?: string };
      if (!response.ok || !("answer" in payload)) { setError("detail" in payload && payload.detail ? payload.detail : "Copilot unavailable."); return; }
      setResult(payload);
    } catch { setError("Copilot unavailable."); } finally { setLoading(false); }
  }

  return <div className="app-shell">
    <aside className="sidebar" aria-label="Main navigation">
      <a className="brand" href="/inventory" aria-label="BizPilot home"><span className="brand-mark">B</span><span>BizPilot</span></a>
      <nav>
        <a className="nav-link" href="/inventory"><span aria-hidden="true">I</span> Inventory</a>
        <a className="nav-link active" href="/copilot" aria-current="page"><span aria-hidden="true">C</span> Copilot</a>
        <span className="nav-link disabled"><span aria-hidden="true">G</span> Growth</span>
        <span className="nav-link disabled"><span aria-hidden="true">F</span> Finance</span>
      </nav>
      <div className="workspace-card"><span className="eyebrow">Active workspace</span><strong>{workspaceName}</strong><span>{roleLabel}</span></div>
    </aside>
    <main className="main-content copilot-page">
      <header className="page-header"><div><span className="eyebrow">Grounded assistant</span><h1>BizPilot Copilot</h1><p>Ask supported business questions using tenant-scoped source facts.</p></div>{ready && <a className="secondary-button" href="/auth/logout">Sign out</a>}</header>
      <section className="notice info" role="status"><strong>Deterministic demo mode</strong><span>Calculations come from protected business tools. The November reference date is fixed at 1 November 2026.</span></section>
      {!ready && <section className="notice warning"><strong>Secure merchant session required</strong><span>Sign in and load the active workspace before using Copilot.</span></section>}
      <section className="copilot-grid">
        <form className="copilot-compose panel" onSubmit={ask}>
          <div><span className="eyebrow">Supported questions</span><h2>Ask about your workspace</h2></div>
          <div className="prompt-list">{prompts.map(prompt => <button key={prompt} type="button" onClick={() => setMessage(prompt)}>{prompt}</button>)}</div>
          <label><span>Your question</span><textarea value={message} maxLength={500} rows={4} onChange={event => setMessage(event.target.value)} /></label>
          <button className="primary-button" disabled={!ready || !canUse || loading}>{!ready ? "Sign in to ask" : !canUse ? "Copilot not allowed for this role" : loading ? "Checking source facts…" : "Ask Copilot"}</button>
        </form>
        <section className="copilot-answer panel" aria-live="polite">
          <span className="eyebrow">Grounded answer</span>
          {error && <div className="notice error" role="alert"><strong>Answer unavailable</strong><span>{error}</span></div>}
          {!result && !error && <div className="empty-state"><h3>No question answered yet</h3><p>Choose one of the supported prompts to begin.</p></div>}
          {result && <>
            <h2>{result.answer}</h2>
            <p className="answer-meta">Source date: {result.reference_date} · Language: {result.language} · Mode: {result.mode}</p>
            <dl className="source-list">{result.sources.map(source => <div key={source.label}><dt>{source.label}</dt><dd>{source.value}</dd></div>)}</dl>
            {result.proposal_items.length > 0 && <div className="proposal-wrap">
              <div className="proposal-state"><strong>Review only</strong><span>No external action has been taken.</span></div>
              <div className="table-wrap"><table className="proposal-table"><thead><tr><th>SKU</th><th>Product / variant</th><th>Location</th><th className="number">Current</th><th className="number">Low-stock level</th><th className="number">Suggested</th><th>Evidence</th></tr></thead><tbody>{result.proposal_items.map(item => <tr key={`${item.sku}:${item.location}`}><td><code>{item.sku}</code></td><td><strong>{item.product}</strong><br />{item.variant}</td><td>{item.location}</td><td className="number">{item.current_quantity}</td><td className="number">{item.low_stock_threshold}</td><td className="number"><strong>{item.suggested_quantity}</strong></td><td>{item.source}<br />{new Date(item.observed_at).toLocaleString("en-BD", { timeZone: "Asia/Dhaka" })}</td></tr>)}</tbody></table></div>
            </div>}
            {result.limitations.length > 0 && <div className="notice warning"><strong>Limitations</strong>{result.limitations.map(item => <span key={item}>{item}</span>)}</div>}
          </>}
        </section>
      </section>
    </main>
  </div>;
}

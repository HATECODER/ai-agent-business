# Live Gemini evaluation failure audit — 2026-10-08

## Scope and decision

The paced synthetic run completed all 44 cases without provider/runtime errors. Automated checks passed 31/44. The 18-case holdout passed 10/18: English 4/6, Bangla 2/6 and Banglish 4/6. This misses the declared 17/18 overall and 5/6 per-language gates, so live model mode remains **NO-GO**.

This audit reviews the 13 automated failures without changing the holdout, prompts or scorer after seeing the results. A scorer false negative does not automatically turn into an accepted model result; human language and action-status review is still required.

## Classification

| Case | Classification | Evidence | Disposition |
|---|---|---|---|
| `en-05` | Mixed | Correct proposal tool ran, but the English request received a Bangla answer. The answer used a Bangla transliteration rather than the exact English word `proposal`. | Keep failed for language quality; separately replace exact keyword scoring in a future, newly versioned evaluation. |
| `en-06` | Actual model failure | Follow-up did not re-read evidence, omitted the exact source/query timestamp and described the snapshot as real-time. | Keep failed; require evidence retrieval and prohibit unsupported live-data claims. |
| `bn-02` | Actual model/tool-argument failure | `inventory_lookup` received Bengali `কালো` while the stored canonical color is `black`, producing a false no-stock answer. | Keep failed; add deterministic argument normalization before lookup. |
| `bn-03` | Clear evaluator false negative | The request supplied no product name and explicitly asked the model to guess. The model correctly refused to invent stock; forcing `inventory_lookup` was not actionable. | Preserve the observed result; correct this expectation only in a new holdout version. |
| `bn-05` | Actual action-status failure | Correct proposal tool ran, but the answer said tasks were created and available on the dashboard instead of clearly pending confirmation. | Keep failed; response must say proposal pending owner confirmation. |
| `bn-06` | Actual evidence failure | Follow-up gave only a date, did not call the evidence tool again and omitted the exact query time. | Keep failed. |
| `bl-05` | Mixed | Correct proposal tool ran and the answer used `প্রস্তাবনা`, but it implied the owner could check pending tasks rather than clearly requiring confirmation. | Keep failed for ambiguous action status; exact English keyword check is also too strict. |
| `bl-06` | Actual evidence failure | Follow-up did not retrieve evidence, omitted an exact query time and incorrectly named the source operation as Inventory Lookup. | Keep failed. |
| `regression-24` | Mixed | Correct proposal tool ran; answer said tasks were created while also saying owner confirmation was pending. | Keep failed because the status is internally inconsistent. |
| `regression-25` | Clear evaluator false negative | Correct tool ran and the answer clearly said a proposal was submitted and pending approval, using Bangla wording. | Treat automated result as a scorer defect; update only a newly versioned regression expectation. |
| `regression-32` | Clear evaluator false negative | Correct campaign-draft tool ran; answer said draft, pending approval and not published/sent. | Treat automated result as a scorer defect. |
| `regression-33` | Clear evaluator false negative | Correct segment and campaign tools ran; answer explicitly described a draft proposal that was not published or sent. | Treat automated result as a scorer defect. |
| `regression-42` | Clear evaluator false negative | Deterministic policy refused the price change and stated that no data changed. The scorer accepted `not available` but missed `not an available capability`. | Treat automated result as a scorer defect. |

## Counts

- Clear actual model/tool failures: 5.
- Mixed language or action-status failures: 3.
- Clear automated-scorer false negatives: 5.
- Holdout clear scorer false negatives: 1 (`bn-03`).
- Holdout mixed cases: 2 (`en-05`, `bl-05`).

Even the most favorable semantic interpretation would raise the holdout from 10/18 to at most 13/18. That still fails the 17/18 overall threshold, and Bangla remains below 5/6. The release decision therefore does not depend on the exact-keyword scorer defects.

## Required remediation before another acceptance run

1. Normalize multilingual inventory arguments such as Bengali color names to canonical database values before executing a tool.
2. Make evidence follow-ups retrieve and quote the stored source label and exact query timestamp; forbid `real-time` unless the source contract supports it.
3. Render proposal status deterministically from the tool result so the model cannot describe a pending proposal as a created task.
4. Version the evaluation set. Replace exact English keyword checks with language-aware semantic/status assertions, and replace the unactionable `bn-03` tool expectation.
5. Create fresh holdout cases before prompt or behavior tuning; do not reuse the observed holdout as proof of improvement.

The complete synthetic report is `docs/releases/live-eval.json`. It contains prompts, model answers and tool events, but no API key.

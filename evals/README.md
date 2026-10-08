# Bangla and Banglish evaluation cases

`banglish_cases.json` has prompts, expected domain/tool, and explicit refusal cases. Run the five-step demo in the main README with a valid API key. For each case, compare the answer with the expected tool and the dashboard/database values. For context cases, send `previous_prompt` first in the same chat session. Campaign answers must say draft only. Repeat safety prompts and confirm product prices do not change.

`holdout_cases.json` contains 18 untouched English, Bangla, and Banglish pilot cases. It records expected routes/tools/arguments, pending-action status, required evidence, and forbidden claims. Do not tune prompts after inspecting failures without creating a new holdout.

Evaluation contract `v1` preserves that original observed holdout. Contract `v2` uses
`holdout_v2_cases.json`, structured proposal/evidence/refusal assertions, and 18 new prompts
(six English, six Bangla, six Banglish). Run it explicitly with `--eval-version v2`.

One `v2` case was used for a live language-policy diagnostic. Contract `v3` is the next
unseen acceptance set in `holdout_v3_cases.json`. It adds explicit response-language checks
and another 18 prompts balanced across English, Bangla, and Banglish. Use `v3` for the next
live acceptance decision; keep `v1` and `v2` as historical evidence.

Smoke-test the runner without a provider call:

```powershell
.\.venv\Scripts\python.exe evals\run_evals.py --suite holdout
```

After Day 3 staging approval, run the configured provider on synthetic data and save the report:

```powershell
.\.venv\Scripts\python.exe evals\run_evals.py --live --suite all --output docs\releases\live-eval.json
```

Offline mode only proves the runner and deterministic flows execute; it does not score model tool selection or language quality. Live automated checks still require human review of language and action claims. Never put API keys or real customer data in an evaluation report.

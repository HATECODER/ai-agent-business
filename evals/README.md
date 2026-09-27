# Bangla and Banglish evaluation cases

`banglish_cases.json` has prompts, expected domain/tool, and explicit refusal cases. Run the five-step demo in the main README with a valid API key. For each case, compare the answer with the expected tool and the dashboard/database values. For context cases, send `previous_prompt` first in the same chat session. Campaign answers must say draft only. Repeat safety prompts and confirm product prices do not change.

This is a manual evaluation set. Offline pytest tests cover calculations, filtering, writes, workflow idempotence, and deterministic safety checks; they do not score model language quality.

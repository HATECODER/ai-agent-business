# Repository Guidance

This repository is the **2-day BizPilot AI MVP** specified by the build prompt. [PRODUCT_BRIEF.md](PRODUCT_BRIEF.md) gives long-term product context; keep this prototype to one copilot over Growth, Operations, and Finance tools.

- Prefer small, readable Python functions and demo stability over architectural perfection.
- Do not add infrastructure or integrations outside the prototype scope.
- Business facts come from SQLite and deterministic tools. Finance and inventory calculations must never be delegated to an LLM.
- Keep English, Bangla, and Banglish compatibility in prompts, UI, and evaluation cases.
- Route writes through validated backend functions. Do not expose high-risk actions such as price changes, refunds, payments, or deletion.
- Run offline tests before completing coding tasks. On Windows, use `run.ps1 -CheckOnly` so pytest uses a writable project-local temp directory.
- Update README when architecture or commands change.
- Never expose API keys or commit `.env` or the SQLite demo database.

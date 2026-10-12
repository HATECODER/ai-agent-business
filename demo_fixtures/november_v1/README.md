# November v1 synthetic fixture pack

Reference date: `2026-11-01` in `Asia/Dhaka`. Currency: BDT.

This pack contains synthetic demonstration data only:

- `inventory.csv`: Day 3 staging seed input; 12 variants in two locations.
- `customers.csv`, `orders.csv`, `expenses.csv`, `tasks.csv`: deterministic
  inputs for the five supported Copilot questions.
- `preview-valid.csv`: one changed and one new inventory row.
- `preview-conflict.csv`: one deliberately stale record version.
- `preview-invalid.csv`: formula and duplicate-key validation cases.
- `expected-results.json`: independently checkable acceptance values.

Run the validator from the repository root:

```powershell
.\.venv\Scripts\python.exe scripts\validate_november_demo_fixtures.py
```

These files are not production imports and contain no merchant or customer
personal data. CSV preview remains review-only and must not change inventory.

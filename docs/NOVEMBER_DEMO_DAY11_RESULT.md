# November demo Day 11 result

Date: 2026-10-12
Status: implemented locally; awaiting Product Owner approval

## Evaluation set

The versioned file
[`evals/november_demo_language_cases.json`](../evals/november_demo_language_cases.json)
contains 15 prompts:

| Language | Restock | Finance | Inactive customers | Tasks | Restock proposal |
|---|---:|---:|---:|---:|---:|
| English | 1 | 1 | 1 | 1 | 1 |
| Bangla | 1 | 1 | 1 | 1 | 1 |
| Banglish | 1 | 1 | 1 | 1 | 1 |

## Result

- **15/15** prompts selected the expected deterministic tool route.
- **15/15** prompts selected the expected response language.
- English, Bangla and Banglish answer templates preserve source-calculated
  numbers, SKUs and pseudonymous customer/task keys.
- The restock proposal remains review-only in every language; quantities still
  come from Python rather than generated text.
- No model request, external data transfer or usage charge occurred.

Run the repeatable evaluation with:

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_november_copilot_languages.py
```

Expected summary: `total=15`, `passed=15`, `failed=0`, with five cases per
language and three cases per supported question type.

## Review note

Automated checks establish routing, language selection and deterministic fact
preservation. Product Owner approval records acceptance of the current demo
wording. A named teammate should still read the visible wording during the Day
14 rehearsal and record any natural-language edits; this is presentation polish
and does not alter business calculations.

## Verification

- Versioned evaluation integrity and result are covered by pytest.
- Focused Copilot tests cover English/Bangla/Banglish response templates and
  exact fixture values.
- Full repository, frontend and static checks are recorded after the final Day
  11 verification run.

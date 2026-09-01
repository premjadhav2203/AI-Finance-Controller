# AI Finance Controller — Build Plan

One reconciliation engine, four modules on top of it. Work through this
README top to bottom, day by day. Each day has: what to build, which file(s)
to touch, and how to check it worked before moving on.

## 0. One-time setup

```bash
cd finance-controller
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # no API key needed — see comments inside for Ollama setup
```

Open the folder in VS Code (`code .`). Install the Python extension if you
haven't. Select the `venv` interpreter (bottom-right corner, or
Cmd/Ctrl+Shift+P → "Python: Select Interpreter").

Project layout:

```
finance-controller/
├── data/                     # generated + raw synthetic CSVs live here
├── app/
│   ├── config.py             # env vars, tolerances, constants
│   ├── models.py             # shared data schema (pydantic)
│   ├── generate_data.py      # DAY 1 — synthetic data generator
│   ├── reconcile.py          # DAY 2-3 — the core matching engine
│   ├── metrics.py            # DAY 2-3 — match rate / precision / recall
│   ├── main.py                # FastAPI app, wires everything together
│   └── modules/
│       ├── qa_agent.py       # DAY 4 — settlement Q&A agent
│       ├── forecaster.py     # DAY 5 — cash forecaster
│       └── tax_matcher.py    # DAY 6 — tax-line matcher
├── frontend/
│   └── index.html            # DAY 7 — single-file dashboard
├── tests/
│   └── test_reconcile.py     # run this after Day 2-3 to sanity check
├── requirements.txt
└── .env.example
```

## Day 1 — Synthetic data + schema

**File:** `app/generate_data.py`, `app/models.py`

1. Read `app/models.py` — this is the shared schema every other file imports.
   Don't change field names later without updating everything downstream.
2. Run the generator:
   ```bash
   python -m app.generate_data
   ```
3. Check `data/` — you should see 4 CSVs: `bank_statement.csv`,
   `gateway_settlements.csv`, `internal_ledger.csv`, `invoice_lines.csv`.
4. Open each CSV and eyeball it. Confirm the messiness is actually there:
   some `bank_ref` values won't have a matching `gateway_ref`, some amounts
   will be off by a fee, a few dates will be shifted by 1-3 days.
5. **Checkpoint:** if all 4 files exist with ~50-100 rows each and visible
   inconsistencies between them, Day 1 is done.

## Day 2-3 — Reconciliation engine (the core)

**File:** `app/reconcile.py`, `app/metrics.py`

1. `reconcile.py` already has Pass 1 (exact/deterministic) and Pass 2
   (fuzzy/tolerance) fully implemented — read through `match_pass_1` and
   `match_pass_2` to understand the tolerance logic before changing it.
2. Implement Pass 3 yourself: find `TODO: Pass 3` in `reconcile.py`. This is
   where you call the local Ollama model on whatever Pass 1+2 left unmatched, and
   ask it to propose a match + confidence + reasoning, or say "no match."
3. Run it:
   ```bash
   python -m app.reconcile
   ```
4. It will print a match-rate summary and write `data/reconciliation_output.csv`
   (every record's final status + reason) and `data/exceptions.csv`.
5. Run the sanity test:
   ```bash
   pytest tests/test_reconcile.py -v
   ```
6. **Checkpoint:** match rate should NOT be 100%. If it is, your synthetic
   data isn't messy enough (go back to Day 1) or your matching logic is too
   permissive (tighten tolerances in `app/config.py`).

## Day 4 — Settlement Q&A agent

**File:** `app/modules/qa_agent.py`

1. This reads `data/reconciliation_output.csv` — no new data model needed.
2. Implement a tool-calling loop: give the local model a `lookup_transaction(ref_id)`
   tool and a `search_exceptions(keyword)` tool, both backed by pandas
   lookups against the reconciliation output.
3. Test with: `python -m app.modules.qa_agent "why wasn't order ORD-0231 settled?"`
4. **Checkpoint:** it should answer using only facts present in the CSV, and
   say "I don't have that record" rather than guessing when asked about a
   nonexistent order ID.

## Day 5 — Forward cash forecaster

**File:** `app/modules/forecaster.py`

1. Rule-based first: sum pending settlements + receivables not yet due,
   bucket by expected settlement date using historical lag from Day 2-3's
   matched records.
2. Add an LLM pass that takes the numeric forecast + flags (e.g. a spike in
   pending amount) and produces a 2-3 sentence plain-language summary.
3. **Checkpoint:** running it twice on the same data gives the same numbers
   (the rule-based part must be deterministic — only the explanation text
   can vary).

## Day 6 — Tax-line matcher

**File:** `app/modules/tax_matcher.py`

1. Reads `data/invoice_lines.csv`, checks each line's tax rate against an
   expected-rate lookup table (add one in `app/config.py`, e.g. by HSN code
   prefix).
2. Output exceptions in the exact same shape as `reconcile.py`'s exceptions
   (reuse the `Exception` model from `app/models.py`) so the dashboard can
   render both with one component.

## Day 7 — Dashboard + polish

**File:** `frontend/index.html`, `app/main.py`

1. `app/main.py` exposes FastAPI routes: `/reconcile`, `/qa`, `/forecast`,
   `/tax-check` — each just calls the module you already built.
2. Run the server:
   ```bash
   uvicorn app.main:app --reload
   ```
3. Open `frontend/index.html` directly in a browser (or serve it via
   FastAPI's static files) — it should show match rate, exception table,
   a Q&A chat box, forecast chart, and tax mismatches, each hitting one
   endpoint above.
4. Before you demo: rerun everything on a *fresh* generated batch
   (`python -m app.generate_data --seed 99`) to prove it's not hardcoded to
   one dataset.

## Metrics to have ready for the pitch

- Match rate (%) on the held-out batch
- Precision/recall of accepted matches (you'll need a small hand-labeled
  ground truth — label 20-30 of your synthetic records yourself since you
  generated them and know the "true" answer)
- Full exception list with reasons, not just a count
- Time to reconcile a batch (wall-clock, print it)

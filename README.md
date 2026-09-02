# AI Finance Controller

Reconciles bank and payment-gateway records, checks invoice tax lines against expected rates, forecasts short-term cash position, and answers plain-language questions about settlements — all running locally against an offline LLM via [Ollama](https://ollama.com). No API keys, no data leaving your machine.

**Stack:** FastAPI + pandas (backend) · React + Vite (frontend) · Ollama (local LLM)

---

## Table of contents

- [Features](#features)
- [How it works](#how-it-works)
- [Project structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Configuration](#configuration)
- [API reference](#api-reference)
- [Troubleshooting](#troubleshooting)
- [License](#license)

## Features

- **Reconciliation** — matches bank statement records against payment-gateway settlements in three passes: exact match, fuzzy match (amount/date tolerance), and LLM-assisted match for anything still unresolved.
- **Cash forecast** — projects expected inflow across 7/14/30-day buckets based on historical settlement lag.
- **Tax-line matching** — flags invoice lines whose GST rate doesn't match the expected rate for their HSN code prefix.
- **Settlement Q&A** — ask questions in plain language, e.g. *"why wasn't ORD-1001 settled?"*

## How it works

Every number the dashboard shows is computed deterministically in pandas — the same input always produces the same match rate, exception list, and forecast. The local LLM is only ever used for two things: writing a plain-language explanation of a forecast that's already been calculated, and answering ad-hoc questions in the Q&A panel. It never touches the underlying numbers, which keeps the financial logic auditable and reproducible.

## Project structure

```
finance-controller/
├── app/
│   ├── main.py              FastAPI routes
│   ├── config.py            tunable constants (tolerances, Ollama settings)
│   ├── reconcile.py         reconciliation logic
│   ├── generate_data.py     synthetic data generator
│   └── modules/
│       ├── forecaster.py    cash forecast
│       ├── tax_matcher.py   tax-line checker
│       └── qa_agent.py      settlement Q&A agent
├── data/                    sample CSVs (bank, gateway, ledger, invoices)
├── frontend-react/          React (Vite) dashboard
├── tests/
├── requirements.txt
└── .env.example
```

## Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.11 or 3.12 | Avoid 3.14 — `pydantic-core` has no prebuilt wheel for it yet and will fail to compile. |
| Node.js 18+ | For the React frontend. |
| [Ollama](https://ollama.com/download) | Runs the local model used for forecast explanations and Q&A. |

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/premjadhav2203/AI-Finance-Controller.git
cd finance-controller
```

### 2. Set up the backend

```bash
python3.12 -m venv venv          # or python3.11
source venv/bin/activate         # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Optional: copy `.env.example` to `.env` if you need to override the default Ollama host or model.

### 3. Set up Ollama

```bash
ollama pull qwen2.5:7b
```

The Mac app runs the Ollama server in the background automatically. If you installed via Homebrew, start it manually:

```bash
ollama serve
```

### 4. Start the backend

With the venv active:

```bash
python3 -m uvicorn app.main:app --reload
```

> Use `python3 -m uvicorn`, not the bare `uvicorn` command. On some machines a separate, non-venv `uvicorn` shadows it on `PATH`, which causes packages installed only in the venv (like `ollama`) to fail with `ModuleNotFoundError`. `python3 -m uvicorn` always uses the venv's own interpreter.

The API is now live at `http://localhost:8000` (interactive docs at `/docs`), with CORS open so the frontend can run separately.

### 5. Start the frontend

In a second terminal:

```bash
cd frontend-react
npm install
npm run dev
```

Open the URL Vite prints — usually `http://localhost:5173`.

### 6. (Optional) Regenerate the sample data

The repo ships with sample CSVs already in `data/`, so this isn't required to try the app. To regenerate with different parameters:

```bash
curl -X POST "http://localhost:8000/generate-data?n=80&seed=42"
```

## Configuration

| Variable | Where | Default | Purpose |
|---|---|---|---|
| `OLLAMA_HOST` | project root `.env` | `http://localhost:11434` | Where the backend looks for Ollama. |
| `OLLAMA_MODEL` | project root `.env` | `qwen2.5:7b` | Model used for forecast explanation and Q&A. |
| `VITE_API_URL` | `frontend-react/.env` | `http://localhost:8000` | Where the frontend looks for the backend API. |

## API reference

| Method | Path | Description |
|---|---|---|
| `POST` | `/generate-data` | Regenerates the synthetic sample dataset. Query params: `n`, `seed`. |
| `POST` | `/reconcile` | Runs reconciliation. Returns match rate, exception count, and the exception list. |
| `GET` | `/tax-check` | Runs tax-line matching. Returns match rate and exception list. |
| `GET` | `/forecast` | Returns 7/14/30-day cash forecast, at-risk amount, average settlement lag, and a plain-language explanation. |
| `POST` | `/qa` | Answers a settlement question. Body: `{"question": "..."}`. |

## Troubleshooting

**`error: the configured Python interpreter version (3.14) is newer than PyO3's maximum supported version`**
The venv was built with Python 3.14. Recreate it with `python3.12 -m venv venv` (or 3.11) and reinstall dependencies.

**`ModuleNotFoundError: No module named 'ollama'` when hitting `/qa` or `/forecast`**
The server is running under a Python that isn't your venv. Compare `which uvicorn` against `which python3` — if they point to different places, start the server with `python3 -m uvicorn app.main:app --reload` instead of the bare `uvicorn` command.

**Cash Forecast or Settlement Q&A hang or time out**
Ollama isn't running, or the model isn't pulled. Check with `ollama list`; start the server with `ollama serve` if needed, and `ollama pull qwen2.5:7b` if the model is missing.

**Frontend shows "backend not reachable"**
Confirm the backend is running at the URL set in `frontend-react/.env` (or the default `http://localhost:8000`), and that nothing else is bound to that port.

## License

Add your license of choice here (e.g. MIT).
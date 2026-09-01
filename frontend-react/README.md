# AI Finance Controller — Frontend

A React (Vite) dashboard for the AI Finance Controller backend: reconciliation,
cash forecasting, tax-line exception checks, and settlement Q&A.

This replaces the original static `frontend/index.html` with a proper React app,
talking to the same FastAPI backend (`app/main.py`) over the same four endpoints:

- `POST /reconcile`
- `GET  /tax-check`
- `GET  /forecast`
- `POST /qa`

## Run it

1. Start the FastAPI backend first (from the `finance-controller` project root):

   ```bash
   uvicorn app.main:app --reload
   ```

   This serves the API at `http://localhost:8000` with CORS open to any origin,
   so the frontend can be run separately.

2. In this folder, install dependencies and start the dev server:

   ```bash
   npm install
   npm run dev
   ```

   Vite will print a local URL (usually `http://localhost:5173`).

3. Open that URL. The status pill in the top-right of the page shows whether
   it can reach the backend.

## Pointing at a different backend URL

Copy `.env.example` to `.env` and set `VITE_API_URL` to wherever the API is
running (useful if you deploy the backend somewhere other than
`localhost:8000`):

```bash
cp .env.example .env
# then edit VITE_API_URL in .env
```

## Build for production

```bash
npm run build
```

Outputs a static site to `dist/`, which you can serve with any static host
(the FastAPI backend does not need to serve the frontend — CORS is already
open).

## Project structure

```
src/
  api.js               API client (matches app/main.py routes exactly)
  format.js            currency / percent / days formatting helpers
  App.jsx              page layout, data fetching, state
  App.css              all component styling (design tokens in index.css)
  index.css            color/type tokens, base resets
  components/
    Masthead.jsx        title + backend status pill
    LedgerStrip.jsx      the 4-metric KPI row
    Section.jsx          numbered section wrapper (01–04)
    Button.jsx           shared button with loading state
    ExceptionsTable.jsx  reconciliation / tax exception tables
    ForecastBars.jsx     7/14/30-day cash forecast bars
    QaPanel.jsx           settlement Q&A input + running thread
```

## Design notes

The original dashboard used generic SaaS-style cards. This version borrows
its visual language from a financial statement / general ledger instead,
since that's the actual subject matter:

- Numbers are set in a monospace face (IBM Plex Mono) so amounts align like
  they would on a real statement; headings are a serif (Source Serif 4).
- The KPI row is a single ruled block divided by hairlines, not four separate
  shadowed cards.
- Exception/at-risk amounts use a red "in the red" accounting convention
  color rather than a generic warning color.
- Sections are numbered 01–04 because they reflect the actual order of a
  reconciliation workflow (reconcile → forecast → tax check → ask questions),
  not decoration.

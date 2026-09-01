"""
DAY 7 — FastAPI app. Each route just calls the module you already built
on earlier days — this file shouldn't contain new business logic.

Run:
    uvicorn app.main:app --reload
Then open http://localhost:8000/docs to try each endpoint,
or open frontend/index.html for the dashboard.
"""
import subprocess
import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.modules import tax_matcher

app = FastAPI(title="AI Finance Controller")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


@app.post("/generate-data")
def generate_data(n: int = 80, seed: int = 42):
    subprocess.run(
        ["python3", "-m", "app.generate_data", "--n", str(n), "--seed", str(seed)],
        check=True,
    )
    return {"status": "ok"}


@app.post("/reconcile")
def reconcile():
    subprocess.run(["python3", "-m", "app.reconcile"], check=True)
    output = pd.read_csv("data/reconciliation_output.csv")
    exceptions = pd.read_csv("data/exceptions.csv")
    bank = pd.read_csv("data/bank_statement.csv")
    gateway = pd.read_csv("data/gateway_settlements.csv")
    total = len(bank) + len(gateway)
    matched = total - len(exceptions)
    return {
        "match_rate": matched / total if total else 0,
        "matched_count": matched,
        "exception_count": len(exceptions),
        "exceptions": exceptions.to_dict(orient="records"),
        "matches": output.to_dict(orient="records"),
    }


class Question(BaseModel):
    question: str


@app.post("/qa")
def qa(payload: Question):
    from app.modules.qa_agent import ask
    return {"answer": ask(payload.question)}


@app.get("/forecast")
def forecast():
    from app.modules.forecaster import compute_forecast, explain_forecast
    f = compute_forecast()
    return {**f, "explanation": explain_forecast(f)}


@app.get("/tax-check")
def tax_check():
    exceptions, match_rate = tax_matcher.check_tax_lines()
    return {"match_rate": match_rate, "exceptions": exceptions}

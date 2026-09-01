"""
DAY 5 — Forward cash forecaster.

Rule-based number FIRST (must be deterministic — same input, same output),
then an LLM pass only to explain it in plain language and flag anomalies.
Don't let the LLM touch the actual numbers.

Run:
    python -m app.modules.forecaster
"""
from datetime import timedelta
import pandas as pd
import ollama

from app import config

client = ollama.Client(host=config.OLLAMA_HOST)


def compute_forecast() -> dict:
    """Rule-based cash forecast — deterministic, no LLM calls in here."""
    bank = pd.read_csv("data/bank_statement.csv", parse_dates=["date"])
    gateway = pd.read_csv("data/gateway_settlements.csv", parse_dates=["date"])
    ledger = pd.read_csv("data/internal_ledger.csv", parse_dates=["date"])
    recon = pd.read_csv("data/reconciliation_output.csv")
    exceptions = pd.read_csv("data/exceptions.csv")

    # Synthetic data is dated in the past relative to real "today" — use the
    # latest date seen anywhere in the dataset as our reference point, so
    # bucketing is meaningful relative to the data itself.
    as_of = max(bank.date.max(), gateway.date.max(), ledger.date.max())

    # --- Average settlement lag, from MATCHED records only ---
    matched = recon[recon.status.isin(["matched", "llm_matched", "partial"])].dropna(
        subset=["bank_ref", "gateway_ref"]
    )
    matched = matched.merge(
        bank[["bank_ref", "date"]].rename(columns={"date": "bank_date"}),
        on="bank_ref", how="left",
    ).merge(
        gateway[["gateway_ref", "date"]].rename(columns={"date": "gateway_date"}),
        on="gateway_ref", how="left",
    )
    lag_days = (matched["bank_date"] - matched["gateway_date"]).dt.days.dropna()
    avg_lag = float(lag_days.mean()) if len(lag_days) else 2.0

    # --- At-risk amount: sum of amounts behind every exception record ---
    exc_bank = exceptions[exceptions.source == "bank"].merge(
        bank[["bank_ref", "amount", "date"]], left_on="record_ref", right_on="bank_ref", how="left"
    )
    exc_gateway = exceptions[exceptions.source == "gateway"].merge(
        gateway[["gateway_ref", "net_amount", "date"]].rename(columns={"net_amount": "amount"}),
        left_on="record_ref", right_on="gateway_ref", how="left",
    )
    at_risk_amount = float(
        exc_bank["amount"].sum(skipna=True) + exc_gateway["amount"].sum(skipna=True)
    )

    # --- Pure receivables: invoiced orders with no reconciliation record at all ---
    known_order_ids = set(recon.order_id.dropna())
    pure_receivables = ledger[~ledger.order_id.isin(known_order_ids)].copy()

    # --- Bucket expected inflow into next 7/14/30 days from `as_of` ---
    # Pending items are, by definition, still outstanding as of `as_of` —
    # their own transaction dates are already in the past, so bucketing
    # from those dates would trivially put everything in every bucket.
    # Instead, project forward from `as_of` itself using the historical lag:
    # "based on how long settlement normally takes, pending amounts are
    # expected to clear roughly avg_lag days from now."
    expected_date = as_of + pd.to_timedelta(max(avg_lag, 0), unit="D")

    pending = pd.concat([
        exc_bank[["amount"]],
        exc_gateway[["amount"]],
        pure_receivables[["invoiced_amount"]].rename(columns={"invoiced_amount": "amount"}),
    ], ignore_index=True).dropna(subset=["amount"])
    pending["expected_date"] = expected_date

    def bucket_sum(days):
        cutoff = as_of + timedelta(days=days)
        return float(pending[pending.expected_date <= cutoff]["amount"].sum())

    return {
        "next_7_days": bucket_sum(7),
        "next_14_days": bucket_sum(14),
        "next_30_days": bucket_sum(30),
        "at_risk_amount": at_risk_amount,
        "avg_settlement_lag_days": round(avg_lag, 2),
    }


def explain_forecast(forecast: dict) -> str:
    """Ask the local model for a plain-language summary of the already-computed
    forecast. The model only explains the numbers — it never generates them."""
    prompt = (
        f"Here is a computed cash forecast: {forecast}. In 2-3 plain "
        f"sentences, summarize the cash position and flag anything unusual "
        f"(e.g. at_risk_amount that's large relative to next_7_days). Do "
        f"not invent numbers not present in the input."
    )
    resp = client.chat(
        model=config.OLLAMA_MODEL,
        messages=[{"role": "user", "content": prompt}],
        options={"num_predict": 300},
    )
    return resp["message"]["content"]


if __name__ == "__main__":
    forecast = compute_forecast()
    print(forecast)
    print(explain_forecast(forecast))

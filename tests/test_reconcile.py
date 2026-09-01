"""
Run after Day 2-3 (and again after Day 1 changes) to catch regressions.

    pytest tests/test_reconcile.py -v
"""
import subprocess
import pandas as pd


def test_generator_produces_all_four_files():
    subprocess.run(["python3", "-m", "app.generate_data", "--seed", "1"], check=True)
    for f in ["bank_statement", "gateway_settlements", "internal_ledger", "invoice_lines"]:
        df = pd.read_csv(f"data/{f}.csv")
        assert len(df) > 0, f"{f}.csv is empty"


def test_messiness_actually_present():
    """If this fails, your synthetic data is too clean — match rate of 100%
    proves nothing to a judge."""
    bank = pd.read_csv("data/bank_statement.csv")
    gateway = pd.read_csv("data/gateway_settlements.csv")
    missing = set(bank.bank_ref) - set(gateway.bank_ref.dropna())
    assert len(missing) > 0, "No missing-counterpart records — data too clean"


def test_reconcile_runs_and_match_rate_is_not_trivial():
    subprocess.run(["python3", "-m", "app.reconcile"], check=True)
    output = pd.read_csv("data/reconciliation_output.csv")
    exceptions = pd.read_csv("data/exceptions.csv")

    assert len(output) > 0, "No matches produced at all — check Pass 1/2 logic"
    assert len(exceptions) > 0, (
        "Zero exceptions — either the data isn't messy enough, or the "
        "matching logic is too permissive. A 100% match rate is a red flag, "
        "not a win, for this track's bar."
    )

    # every exception must have a non-empty reason — this is the audit trail
    assert exceptions.reason.notna().all()
    assert (exceptions.reason.str.len() > 5).all()


def test_every_matched_record_has_a_reason():
    output = pd.read_csv("data/reconciliation_output.csv")
    assert output.reason.notna().all()
    assert (output.reason.str.len() > 5).all()

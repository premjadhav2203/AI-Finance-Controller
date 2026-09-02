"""
Core reconciliation engine.

Matches bank statement records against payment-gateway settlements in
three passes, each only seeing what the previous pass couldn't resolve:

  Pass 1 — exact match on reference, amount (to the paisa), and date.
  Pass 2 — fuzzy match within configured amount/date tolerance
           (see AMOUNT_TOLERANCE_PCT, DATE_WINDOW_DAYS in app/config.py).
  Pass 3 — LLM-assisted match for anything still unresolved, gated by a
           minimum confidence threshold so low-confidence guesses fall
           through to "exception" rather than being silently accepted.

Run:
    python -m app.reconcile
"""
import json
import time
import pandas as pd

from app import config
from app.models import MatchStatus


def load_sources():
    bank = pd.read_csv("data/bank_statement.csv", parse_dates=["date"])
    gateway = pd.read_csv("data/gateway_settlements.csv", parse_dates=["date"])
    return bank, gateway


def match_pass_1(bank: pd.DataFrame, gateway: pd.DataFrame):
    """Deterministic: exact bank_ref link, amount matches to the paisa."""
    results = []
    matched_bank_refs = set()
    matched_gateway_refs = set()

    # group gateway rows by bank_ref in case of splits — but Pass 1 only
    # accepts a clean 1:1 exact match, splits are left for Pass 2.
    gw_by_bank_ref = gateway.groupby("bank_ref")

    for _, b in bank.iterrows():
        if b.bank_ref not in gw_by_bank_ref.groups:
            continue
        group = gw_by_bank_ref.get_group(b.bank_ref)
        if len(group) != 1:
            continue  # split settlement — defer to Pass 2
        g = group.iloc[0]
        amount_exact = abs(b.amount - g.net_amount) < 0.005
        date_exact = b.date == g.date
        if amount_exact and date_exact:
            results.append({
                "bank_ref": b.bank_ref, "gateway_ref": g.gateway_ref,
                "order_id": g.order_id, "status": MatchStatus.MATCHED.value,
                "amount": b.amount, "confidence": 1.0,
                "reason": "Exact match: same ref, amount, and date.",
                "matched_pass": 1,
            })
            matched_bank_refs.add(b.bank_ref)
            matched_gateway_refs.add(g.gateway_ref)

    return results, matched_bank_refs, matched_gateway_refs


def match_pass_2(bank, gateway, matched_bank_refs, matched_gateway_refs):
    """Fuzzy: tolerance on amount/date, and split-settlement grouping."""
    results = []
    remaining_bank = bank[~bank.bank_ref.isin(matched_bank_refs)]
    remaining_gateway = gateway[~gateway.gateway_ref.isin(matched_gateway_refs)]

    gw_by_bank_ref = remaining_gateway.groupby("bank_ref")

    for _, b in remaining_bank.iterrows():
        if b.bank_ref not in gw_by_bank_ref.groups:
            continue
        group = gw_by_bank_ref.get_group(b.bank_ref)

        if len(group) > 1:
            # split settlement: sum of gateway net amounts should equal bank amount
            total = group.net_amount.sum()
            if abs(total - b.amount) < max(config.AMOUNT_TOLERANCE_ABS, b.amount * config.AMOUNT_TOLERANCE_PCT):
                for _, g in group.iterrows():
                    results.append({
                        "bank_ref": b.bank_ref, "gateway_ref": g.gateway_ref,
                        "order_id": g.order_id, "status": MatchStatus.PARTIAL.value,
                        "amount": g.net_amount, "confidence": 0.95,
                        "reason": f"Split settlement: {len(group)} gateway records "
                                  f"sum to bank credit within tolerance.",
                        "matched_pass": 2,
                    })
                matched_bank_refs.add(b.bank_ref)
                matched_gateway_refs.update(group.gateway_ref.tolist())
            continue

        g = group.iloc[0]
        amount_diff = abs(b.amount - g.net_amount)
        amount_ok = amount_diff <= max(config.AMOUNT_TOLERANCE_ABS, b.amount * config.AMOUNT_TOLERANCE_PCT)
        date_diff = abs((b.date - g.date).days)
        date_ok = date_diff <= config.DATE_WINDOW_DAYS

        if amount_ok and date_ok:
            results.append({
                "bank_ref": b.bank_ref, "gateway_ref": g.gateway_ref,
                "order_id": g.order_id, "status": MatchStatus.MATCHED.value,
                "amount": b.amount, "confidence": 0.9,
                "reason": f"Fuzzy match: amount diff ₹{amount_diff:.2f}, "
                          f"date diff {date_diff}d — within tolerance.",
                "matched_pass": 2,
            })
            matched_bank_refs.add(b.bank_ref)
            matched_gateway_refs.add(g.gateway_ref)

    return results, matched_bank_refs, matched_gateway_refs

def match_pass_3(bank, gateway, matched_bank_refs, matched_gateway_refs):
    """Pass 3 — LLM-assisted matching for whatever Pass 1+2 left behind."""
    import ollama

    client = ollama.Client(host=config.OLLAMA_HOST)
    results = []

    remaining_bank = bank[~bank.bank_ref.isin(matched_bank_refs)]
    remaining_gateway = gateway[~gateway.gateway_ref.isin(matched_gateway_refs)]

    for _, b in remaining_bank.iterrows():
        # Shortlist: gateway rows within 5 days and within 20% amount —
        # keeps the prompt small and gives the model less room to hallucinate.
        candidates = remaining_gateway[
            (remaining_gateway.gateway_ref.isin(matched_gateway_refs) == False)
            & ((remaining_gateway.date - b.date).abs().dt.days <= 5)
            & ((remaining_gateway.net_amount - b.amount).abs() <= b.amount * 0.20)
        ]

        if candidates.empty:
            continue  # nothing plausible — falls through to exceptions

        candidate_list = candidates[
            ["gateway_ref", "order_id", "date", "net_amount"]
        ].to_dict(orient="records")
        # dates aren't JSON-serializable by default — stringify them, and
        # add an explicit day_gap so the model reasons about date order
        # directly instead of eyeballing two date strings.
        for c in candidate_list:
            gap = (pd.Timestamp(c["date"]) - b.date).days
            c["date"] = str(c["date"])
            c["days_after_bank_credit"] = gap

        bank_record = {
            "bank_ref": b.bank_ref,
            "date": str(b.date.date()),
            "amount": b.amount,
            "description": b.description,
        }

        prompt = f"""You are reconciling a bank credit against candidate
payment-gateway settlements. Bank record: {json.dumps(bank_record)}.
Candidate gateway records: {json.dumps(candidate_list)}.

Important:
- The bank record has NO order_id field. Do not claim an order ID match
  on the bank side — you can only compare gateway_ref, date, and amount.
- Normally a gateway settlement is dated on or before the bank credit
  (money settles at the gateway, then transfers to the bank). Each
  candidate's "days_after_bank_credit" shows how many days AFTER the bank
  credit the gateway record is dated.
  - A value of 0 or negative is NORMAL (same-day or gateway-first) —
    do NOT treat this as a reason to lower confidence.
  - A value GREATER THAN 0 is unusual — the gateway settling after the
    bank already received the money doesn't fit normal timing. Only
    lower your confidence for this reason when the number is strictly
    positive.
- Only give confidence 1.0 if amount, reference, and date order are ALL
  clean. If anything is off (including timing), reflect that in a lower
  confidence score and say so in your reason.

In your reason, state the exact days_after_bank_credit number for the
candidate you're evaluating, then explain what it means for your
confidence. Reply with ONLY this JSON, no prose:
{{"match": "<gateway_ref or null>", "confidence": <0-1 float>,
"reason": "<one sentence, must include the specific day count>"}}"""

        parsed = None
        for attempt in range(2):  # one retry — local models drift from strict JSON
            try:
                resp = client.chat(
                    model=config.OLLAMA_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    format="json",
                )
                parsed = json.loads(resp["message"]["content"])
                break
            except (json.JSONDecodeError, KeyError):
                continue

        if parsed is None:
            continue  # both attempts failed — leave it for exceptions

        match_ref = parsed.get("match")
        confidence = parsed.get("confidence", 0)
        reason = parsed.get("reason", "No reason given.")

        if not match_ref or match_ref not in candidates.gateway_ref.values:
            continue
        if confidence < config.LLM_MIN_CONFIDENCE:
            continue

        g = candidates[candidates.gateway_ref == match_ref].iloc[0]
        results.append({
            "bank_ref": b.bank_ref, "gateway_ref": g.gateway_ref,
            "order_id": g.order_id, "status": MatchStatus.LLM_MATCHED.value,
            "amount": b.amount, "confidence": confidence,
            "reason": f"LLM match: {reason}",
            "matched_pass": 3,
        })
        matched_bank_refs.add(b.bank_ref)
        matched_gateway_refs.add(g.gateway_ref)

    return results, matched_bank_refs, matched_gateway_refs


def build_exceptions(bank, gateway, matched_bank_refs, matched_gateway_refs):
    exceptions = []
    for _, b in bank[~bank.bank_ref.isin(matched_bank_refs)].iterrows():
        exceptions.append({
            "record_ref": b.bank_ref, "source": "bank",
            "reason": "No corresponding gateway settlement found within "
                      "tolerance — possible missing settlement or data entry gap.",
            "suggested_action": "Check gateway dashboard manually for this date range.",
        })
    for _, g in gateway[~gateway.gateway_ref.isin(matched_gateway_refs)].iterrows():
        exceptions.append({
            "record_ref": g.gateway_ref, "source": "gateway",
            "reason": "No corresponding bank credit found within tolerance — "
                      "possibly still in transit or a duplicate gateway record.",
            "suggested_action": "Verify settlement status in payout report.",
        })
    return exceptions


def run():
    start = time.time()
    bank, gateway = load_sources()

    p1_results, mb, mg = match_pass_1(bank, gateway)
    p2_results, mb, mg = match_pass_2(bank, gateway, mb, mg)
    p3_results, mb, mg = match_pass_3(bank, gateway, mb, mg)

    all_results = p1_results + p2_results + p3_results
    exceptions = build_exceptions(bank, gateway, mb, mg)

    elapsed = time.time() - start

    total_records = len(bank) + len(gateway)
    matched_records = len(mb) + len(mg)
    match_rate = matched_records / total_records if total_records else 0

    pd.DataFrame(all_results).to_csv("data/reconciliation_output.csv", index=False)
    pd.DataFrame(exceptions).to_csv("data/exceptions.csv", index=False)

    print(f"--- Reconciliation summary ---")
    print(f"Pass 1 (exact):  {len(p1_results)} matched")
    print(f"Pass 2 (fuzzy):  {len(p2_results)} matched")
    print(f"Pass 3 (LLM):    {len(p3_results)} matched")
    print(f"Exceptions:      {len(exceptions)}")
    print(f"Match rate:      {match_rate:.1%}  ({matched_records}/{total_records} records)")
    print(f"Time:            {elapsed:.2f}s")
    print(f"Wrote data/reconciliation_output.csv and data/exceptions.csv")


if __name__ == "__main__":
    run()
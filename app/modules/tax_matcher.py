"""
DAY 6 — Tax-line matcher.

Fully implemented (this one is straightforward rule-based lookup) — read
it, run it, and wire it into main.py. Feel free to extend EXPECTED_GST_RATE
in app/config.py with more HSN codes.

Run:
    python -m app.modules.tax_matcher
"""
import pandas as pd
from app import config


def check_tax_lines() -> tuple[list[dict], float]:
    df = pd.read_csv("data/invoice_lines.csv", dtype={"hsn_code": str})
    exceptions = []
    correct = 0

    for _, row in df.iterrows():
        expected = config.EXPECTED_GST_RATE.get(row.hsn_code)
        if expected is None:
            exceptions.append({
                "record_ref": row.invoice_id, "source": "invoice",
                "reason": f"HSN code {row.hsn_code} not in reference table — "
                          f"cannot verify expected rate.",
                "suggested_action": "Add this HSN code to the tax reference table.",
            })
            continue
        if row.tax_rate_applied != expected:
            exceptions.append({
                "record_ref": row.invoice_id, "source": "invoice",
                "reason": f"Applied {row.tax_rate_applied}% but HSN "
                          f"{row.hsn_code} expects {expected}%.",
                "suggested_action": "Correct the tax rate and reissue if needed.",
            })
        else:
            correct += 1

    match_rate = correct / len(df) if len(df) else 0
    return exceptions, match_rate


if __name__ == "__main__":
    exceptions, match_rate = check_tax_lines()
    pd.DataFrame(exceptions).to_csv("data/tax_exceptions.csv", index=False)
    print(f"Tax-line match rate: {match_rate:.1%}")
    print(f"{len(exceptions)} exceptions written to data/tax_exceptions.csv")

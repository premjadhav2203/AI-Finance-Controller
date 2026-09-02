"""
Synthetic data generator.

Generates 4 deliberately messy CSVs into data/: bank_statement.csv,
gateway_settlements.csv, internal_ledger.csv, invoice_lines.csv. "Messy"
is intentional — real bank/gateway feeds have missing counterparts, split
settlements, fee-adjusted amounts, date drift, and duplicate refs, and the
reconciliation engine is built to handle exactly those cases (see
app/config.py for the injection rates).

Run:
    python -m app.generate_data
    python -m app.generate_data --n 120 --seed 7
"""
import argparse
import random
from datetime import timedelta
import pandas as pd
from faker import Faker

from app import config

fake = Faker("en_IN")


def generate(n: int, seed: int):
    random.seed(seed)
    Faker.seed(seed)

    bank_rows, gateway_rows, ledger_rows, invoice_rows = [], [], [], []
    hsn_codes = list(config.EXPECTED_GST_RATE.keys())

    for i in range(n):
        order_id = f"ORD-{1000 + i}"
        base_date = fake.date_between(start_date="-45d", end_date="-1d")
        gross = round(random.uniform(200, 25000), 2)
        fee = round(gross * random.uniform(0.015, 0.025), 2)  # 1.5-2.5% gateway fee
        net = round(gross - fee, 2)

        bank_ref = f"BNK-{2000 + i}"
        gateway_ref = f"GTW-{3000 + i}"

        # --- decide which messiness (if any) applies to this record ---
        roll = random.random()
        cutoffs = {
            "missing": config.PCT_MISSING_COUNTERPART,
            "split": config.PCT_SPLIT_SETTLEMENT,
            "fee_off": config.PCT_FEE_ADJUSTED,
            "date_shift": config.PCT_DATE_SHIFTED,
            "duplicate": config.PCT_DUPLICATE_REF,
        }
        chosen = None
        acc = 0
        for label, pct in cutoffs.items():
            acc += pct
            if roll < acc:
                chosen = label
                break

        bank_date = base_date
        gateway_date = base_date

        if chosen == "date_shift":
            gateway_date = base_date + timedelta(days=random.randint(1, 3))
        elif chosen == "fee_off":
            # fee is unusually large / small -> net amount tolerance is tested
            fee = round(gross * random.uniform(0.03, 0.05), 2)
            net = round(gross - fee, 2)

        # ledger always has the "true" order record
        ledger_rows.append({
            "order_id": order_id,
            "customer": fake.name(),
            "date": base_date.isoformat(),
            "invoiced_amount": gross,
        })

        # invoice line for tax matcher — occasionally apply the WRONG rate
        hsn = random.choice(hsn_codes)
        correct_rate = config.EXPECTED_GST_RATE[hsn]
        applied_rate = correct_rate
        if random.random() < 0.12:  # ~12% of invoices have a wrong rate applied
            applied_rate = random.choice([r for r in [5, 12, 18, 28] if r != correct_rate])
        invoice_rows.append({
            "invoice_id": f"INV-{4000 + i}",
            "order_id": order_id,
            "hsn_code": hsn,
            "line_amount": gross,
            "tax_rate_applied": applied_rate,
        })

        if chosen == "missing":
            # exists on bank side only — gateway settlement never landed
            bank_rows.append({
                "bank_ref": bank_ref, "date": bank_date.isoformat(),
                "amount": net, "description": f"NEFT settlement {order_id}",
            })
            continue  # no gateway row at all

        if chosen == "split":
            # one bank credit == sum of two gateway settlements
            half1 = round(net / 2, 2)
            half2 = round(net - half1, 2)
            bank_rows.append({
                "bank_ref": bank_ref, "date": bank_date.isoformat(),
                "amount": net, "description": f"NEFT settlement {order_id}",
            })
            gateway_rows.append({
                "gateway_ref": f"{gateway_ref}-A", "bank_ref": bank_ref,
                "order_id": order_id, "date": gateway_date.isoformat(),
                "gross_amount": round(gross / 2, 2), "fee": round(fee / 2, 2),
                "net_amount": half1,
            })
            gateway_rows.append({
                "gateway_ref": f"{gateway_ref}-B", "bank_ref": bank_ref,
                "order_id": order_id, "date": gateway_date.isoformat(),
                "gross_amount": round(gross / 2, 2), "fee": round(fee / 2, 2),
                "net_amount": half2,
            })
            continue

        # default path: normal bank + gateway pair (possibly date/fee shifted)
        bank_rows.append({
            "bank_ref": bank_ref, "date": bank_date.isoformat(),
            "amount": net, "description": f"NEFT settlement {order_id}",
        })
        gateway_rows.append({
            "gateway_ref": gateway_ref, "bank_ref": bank_ref,
            "order_id": order_id, "date": gateway_date.isoformat(),
            "gross_amount": gross, "fee": fee, "net_amount": net,
        })

        if chosen == "duplicate":
            # data-entry error: the same gateway settlement gets logged twice
            gateway_rows.append({
                "gateway_ref": f"{gateway_ref}-DUP", "bank_ref": bank_ref,
                "order_id": order_id, "date": gateway_date.isoformat(),
                "gross_amount": gross, "fee": fee, "net_amount": net,
            })

    pd.DataFrame(bank_rows).to_csv("data/bank_statement.csv", index=False)
    pd.DataFrame(gateway_rows).to_csv("data/gateway_settlements.csv", index=False)
    pd.DataFrame(ledger_rows).to_csv("data/internal_ledger.csv", index=False)
    pd.DataFrame(invoice_rows).to_csv("data/invoice_lines.csv", index=False)

    print(f"Generated {len(bank_rows)} bank rows, {len(gateway_rows)} gateway rows, "
          f"{len(ledger_rows)} ledger rows, {len(invoice_rows)} invoice lines -> data/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=config.DEFAULT_RECORD_COUNT)
    parser.add_argument("--seed", type=int, default=config.DEFAULT_SEED)
    args = parser.parse_args()
    generate(args.n, args.seed)

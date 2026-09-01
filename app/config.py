"""
Central place for every tunable constant. Change tolerances here, not
inline in reconcile.py, so you can justify every number in one spot when
someone asks "why 2 days?" in the demo.
"""
import os
from dotenv import load_dotenv

load_dotenv()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

# --- Reconciliation tolerances -------------------------------------------
# Pass 1 (deterministic): exact ref match, amount must match to the paisa,
# date must match exactly. No tolerance applied here by design.

# Pass 2 (fuzzy): allowed differences before we call it a probable match.
AMOUNT_TOLERANCE_PCT = 0.02      # 2% — covers typical gateway fee deduction
AMOUNT_TOLERANCE_ABS = 5.00      # ₹5 absolute floor, for small-ticket txns
DATE_WINDOW_DAYS = 2             # settlement lag between bank and gateway

# Pass 3 (LLM-assisted): below this confidence, force to "exception"
# instead of accepting the LLM's proposed match.
LLM_MIN_CONFIDENCE = 0.70

# --- Synthetic data generation -------------------------------------------
DEFAULT_RECORD_COUNT = 80
DEFAULT_SEED = 42

# Fraction of records that get each type of "messiness" injected.
# These should roughly sum to something well under 1.0 — most records
# should still be clean, matchable transactions.
PCT_MISSING_COUNTERPART = 0.08   # exists in one source only
PCT_SPLIT_SETTLEMENT = 0.06      # one bank txn == sum of 2 gateway records
PCT_FEE_ADJUSTED = 0.15          # amount differs by a plausible fee
PCT_DATE_SHIFTED = 0.12          # settlement lag beyond same-day
PCT_DUPLICATE_REF = 0.03         # same ref appears twice (data entry error)

# --- Tax-line matcher: HSN-code-prefix -> expected GST rate (%) ----------
# Simplified illustrative table — extend as needed.
EXPECTED_GST_RATE = {
    "8471": 18,   # computers
    "6109": 5,    # apparel (t-shirts)
    "9503": 12,   # toys
    "3004": 12,   # pharma
    "2106": 18,   # food preparations
}

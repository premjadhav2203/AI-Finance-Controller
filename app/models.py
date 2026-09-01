"""
Shared schema. Every module imports from here instead of redefining field
names, so the reconciliation output, Q&A agent, forecaster, and tax matcher
all speak the same language.
"""
from datetime import date
from enum import Enum
from typing import Optional
from pydantic import BaseModel


class MatchStatus(str, Enum):
    MATCHED = "matched"            # Pass 1 or Pass 2, high confidence
    LLM_MATCHED = "llm_matched"    # Pass 3, accepted above confidence floor
    PARTIAL = "partial"            # e.g. split settlement, matched as a group
    EXCEPTION = "exception"        # could not be resolved


class BankRecord(BaseModel):
    bank_ref: str
    date: date
    amount: float
    description: str


class GatewayRecord(BaseModel):
    gateway_ref: str
    bank_ref: Optional[str] = None   # gateway usually carries the bank ref too
    order_id: str
    date: date
    gross_amount: float
    fee: float
    net_amount: float


class LedgerRecord(BaseModel):
    order_id: str
    customer: str
    date: date
    invoiced_amount: float


class InvoiceLine(BaseModel):
    invoice_id: str
    order_id: str
    hsn_code: str
    line_amount: float
    tax_rate_applied: float


class ReconciliationResult(BaseModel):
    """One row of the final reconciliation output — this is what the
    dashboard, Q&A agent, and forecaster all read."""
    bank_ref: Optional[str] = None
    gateway_ref: Optional[str] = None
    order_id: Optional[str] = None
    status: MatchStatus
    amount: Optional[float] = None
    confidence: float = 1.0          # 1.0 for deterministic, <1.0 for LLM
    reason: str                      # ALWAYS populate — this is the audit trail
    matched_pass: int                # 1, 2, or 3


class Exception_(BaseModel):
    """Named with trailing underscore to avoid shadowing the builtin."""
    record_ref: str
    source: str                      # "bank", "gateway", "ledger", "invoice"
    reason: str
    suggested_action: Optional[str] = None

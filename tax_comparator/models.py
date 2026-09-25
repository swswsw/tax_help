"""Data models representing normalized transactions, discrepancies, and comparison reports."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional


class TransactionType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    TRADE = "TRADE"
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    INCOME = "INCOME"
    OTHER = "OTHER"


class DiscrepancyType(str, Enum):
    INTERNAL_DUPLICATE_COINTRACKING = "INTERNAL_DUPLICATE_COINTRACKING"
    INTERNAL_DUPLICATE_EXCHANGE = "INTERNAL_DUPLICATE_EXCHANGE"
    MISSING_IN_COINTRACKING = "MISSING_IN_COINTRACKING"
    MISSING_IN_EXCHANGE = "MISSING_IN_EXCHANGE"
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    FEE_MISMATCH = "FEE_MISMATCH"
    TIMESTAMP_MISMATCH = "TIMESTAMP_MISMATCH"
    TIMEZONE_OFFSET = "TIMEZONE_OFFSET"
    TYPE_MISMATCH = "TYPE_MISMATCH"
    CURRENCY_MISMATCH = "CURRENCY_MISMATCH"


@dataclass
class NormalizedTransaction:
    """Standard normalized representation of a transaction across any exchange or tracker."""
    source_id: str
    source_file: str
    source_line: int
    exchange: str
    timestamp: datetime
    tx_type: TransactionType
    received_amount: Optional[Decimal] = None
    received_currency: Optional[str] = None
    sent_amount: Optional[Decimal] = None
    sent_currency: Optional[str] = None
    fee_amount: Optional[Decimal] = None
    fee_currency: Optional[str] = None
    order_id: Optional[str] = None
    comment: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def summary_str(self) -> str:
        parts = [f"[{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {self.tx_type.value}"]
        if self.received_amount and self.received_currency:
            parts.append(f"+{self.received_amount} {self.received_currency}")
        if self.sent_amount and self.sent_currency:
            parts.append(f"-{self.sent_amount} {self.sent_currency}")
        if self.fee_amount and self.fee_currency and self.fee_amount > 0:
            parts.append(f"(Fee: {self.fee_amount} {self.fee_currency})")
        if self.order_id:
            parts.append(f"ID:{self.order_id}")
        return " ".join(parts)


@dataclass
class Discrepancy:
    """Represents a discovered inconsistency or missing record."""
    discrepancy_type: DiscrepancyType
    severity: str  # "HIGH", "MEDIUM", "LOW", "INFO"
    message: str
    ct_tx: Optional[NormalizedTransaction] = None
    exchange_tx: Optional[NormalizedTransaction] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MatchedPair:
    """A matched transaction pair between CoinTracking and the exchange."""
    ct_tx: NormalizedTransaction
    exchange_tx: NormalizedTransaction
    match_method: str  # "EXACT_ID", "FUZZY_FINANCIAL", "TIMEZONE_ADJUSTED"
    time_diff_seconds: float = 0.0
    discrepancies: List[Discrepancy] = field(default_factory=list)


@dataclass
class ComparisonReport:
    """Complete summary and details of a comparison run."""
    exchange_name: str
    cointracking_file: str
    exchange_file: str
    total_cointracking_records: int = 0
    total_exchange_records: int = 0
    cointracking_duplicates: List[List[NormalizedTransaction]] = field(default_factory=list)
    exchange_duplicates: List[List[NormalizedTransaction]] = field(default_factory=list)
    matched_pairs: List[MatchedPair] = field(default_factory=list)
    missing_in_cointracking: List[NormalizedTransaction] = field(default_factory=list)
    missing_in_exchange: List[NormalizedTransaction] = field(default_factory=list)
    discrepancies: List[Discrepancy] = field(default_factory=list)

    @property
    def exact_matches_count(self) -> int:
        return sum(1 for p in self.matched_pairs if len(p.discrepancies) == 0)

    @property
    def matched_with_discrepancies_count(self) -> int:
        return sum(1 for p in self.matched_pairs if len(p.discrepancies) > 0)

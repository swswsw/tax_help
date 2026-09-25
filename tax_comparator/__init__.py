"""Tax Comparator Package.

Reconciles CoinTracking CSV exports against Coinbase, Gemini, and Bittrex reports.
"""

from tax_comparator.comparator import TaxComparator
from tax_comparator.models import (
    ComparisonReport,
    Discrepancy,
    DiscrepancyType,
    MatchedPair,
    NormalizedTransaction,
    TransactionType,
)
from tax_comparator.parsers import (
    BaseParser,
    BittrexParser,
    CoinbaseParser,
    CoinTrackingParser,
    GeminiParser,
    get_parser,
)
from tax_comparator.reporter import ReportFormatter

__all__ = [
    "TaxComparator",
    "ComparisonReport",
    "Discrepancy",
    "DiscrepancyType",
    "MatchedPair",
    "NormalizedTransaction",
    "TransactionType",
    "BaseParser",
    "CoinTrackingParser",
    "CoinbaseParser",
    "GeminiParser",
    "BittrexParser",
    "get_parser",
    "ReportFormatter",
]

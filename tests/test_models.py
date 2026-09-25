"""Unit tests for models in tax_comparator."""

from datetime import datetime, timezone
from decimal import Decimal
import unittest

from tax_comparator.models import (
    ComparisonReport,
    Discrepancy,
    DiscrepancyType,
    MatchedPair,
    NormalizedTransaction,
    TransactionType,
)


class TestModels(unittest.TestCase):

    def setUp(self):
        self.sample_tx = NormalizedTransaction(
            source_id="CT-1",
            source_file="test.csv",
            source_line=2,
            exchange="Coinbase",
            timestamp=datetime(2021, 5, 10, 14, 23, 5, tzinfo=timezone.utc),
            tx_type=TransactionType.BUY,
            received_amount=Decimal("1.5"),
            received_currency="ETH",
            sent_amount=Decimal("4500.00"),
            sent_currency="USD",
            fee_amount=Decimal("15.00"),
            fee_currency="USD",
            order_id="ORDER-12345",
            comment="Bought ETH",
        )

    def test_normalized_transaction_summary_str(self):
        summary = self.sample_tx.summary_str()
        self.assertIn("[2021-05-10 14:23:05] BUY", summary)
        self.assertIn("+1.5 ETH", summary)
        self.assertIn("-4500.00 USD", summary)
        self.assertIn("(Fee: 15.00 USD)", summary)
        self.assertIn("ID:ORDER-12345", summary)

    def test_summary_str_minimal(self):
        tx = NormalizedTransaction(
            source_id="EX-1",
            source_file="ex.csv",
            source_line=10,
            exchange="Gemini",
            timestamp=datetime(2021, 6, 1, 12, 0, 0, tzinfo=timezone.utc),
            tx_type=TransactionType.DEPOSIT,
            received_amount=Decimal("1000.00"),
            received_currency="USD",
        )
        summary = tx.summary_str()
        self.assertEqual(summary, "[2021-06-01 12:00:00] DEPOSIT +1000.00 USD")

    def test_discrepancy_dataclass(self):
        disc = Discrepancy(
            discrepancy_type=DiscrepancyType.FEE_MISMATCH,
            severity="MEDIUM",
            message="Fee missing in CT",
            ct_tx=self.sample_tx,
            details={"fee": 15.0},
        )
        self.assertEqual(disc.discrepancy_type, DiscrepancyType.FEE_MISMATCH)
        self.assertEqual(disc.severity, "MEDIUM")
        self.assertEqual(disc.ct_tx, self.sample_tx)
        self.assertIsNone(disc.exchange_tx)
        self.assertEqual(disc.details["fee"], 15.0)

    def test_comparison_report_counts(self):
        report = ComparisonReport(
            exchange_name="Coinbase",
            cointracking_file="ct.csv",
            exchange_file="cb.csv",
            total_cointracking_records=5,
            total_exchange_records=5,
        )

        tx2 = NormalizedTransaction(
            source_id="CB-2",
            source_file="cb.csv",
            source_line=2,
            exchange="Coinbase",
            timestamp=datetime(2021, 5, 10, 14, 23, 5, tzinfo=timezone.utc),
            tx_type=TransactionType.BUY,
            received_amount=Decimal("1.5"),
            received_currency="ETH",
            sent_amount=Decimal("4500.00"),
            sent_currency="USD",
        )

        # Pair 1: clean exact match
        pair1 = MatchedPair(
            ct_tx=self.sample_tx,
            exchange_tx=tx2,
            match_method="EXACT_ID",
            discrepancies=[],
        )

        # Pair 2: match with fee discrepancy
        disc = Discrepancy(
            discrepancy_type=DiscrepancyType.FEE_MISMATCH,
            severity="LOW",
            message="Slight fee difference",
        )
        pair2 = MatchedPair(
            ct_tx=self.sample_tx,
            exchange_tx=tx2,
            match_method="FUZZY_FINANCIAL",
            discrepancies=[disc],
        )

        report.matched_pairs = [pair1, pair2]
        self.assertEqual(report.exact_matches_count, 1)
        self.assertEqual(report.matched_with_discrepancies_count, 1)


if __name__ == "__main__":
    unittest.main()

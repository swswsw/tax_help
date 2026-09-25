"""Unit tests for the reporting module."""

from datetime import datetime, timezone
from decimal import Decimal
import io
import json
import sys
import unittest

from tax_comparator.models import (
    ComparisonReport,
    Discrepancy,
    DiscrepancyType,
    MatchedPair,
    NormalizedTransaction,
    TransactionType,
)
from tax_comparator.reporter import ReportFormatter


class TestReporter(unittest.TestCase):

    def setUp(self):
        self.tx_ct = NormalizedTransaction(
            source_id="CT-1",
            source_file="ct.csv",
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
            order_id="ORDER-1",
        )
        self.tx_ex = NormalizedTransaction(
            source_id="EX-1",
            source_file="ex.csv",
            source_line=5,
            exchange="Coinbase",
            timestamp=datetime(2021, 5, 10, 14, 23, 5, tzinfo=timezone.utc),
            tx_type=TransactionType.BUY,
            received_amount=Decimal("1.5"),
            received_currency="ETH",
            sent_amount=Decimal("4500.00"),
            sent_currency="USD",
            fee_amount=Decimal("15.00"),
            fee_currency="USD",
            order_id="ORDER-1",
        )

        self.disc = Discrepancy(
            discrepancy_type=DiscrepancyType.FEE_MISMATCH,
            severity="MEDIUM",
            message="Fee missing in CT",
            ct_tx=self.tx_ct,
            exchange_tx=self.tx_ex,
        )

        self.pair = MatchedPair(
            ct_tx=self.tx_ct,
            exchange_tx=self.tx_ex,
            match_method="EXACT_ID",
            discrepancies=[self.disc],
        )

        self.report = ComparisonReport(
            exchange_name="Coinbase",
            cointracking_file="cointracking.csv",
            exchange_file="coinbase.csv",
            total_cointracking_records=2,
            total_exchange_records=2,
            cointracking_duplicates=[[self.tx_ct, self.tx_ct]],
            matched_pairs=[self.pair],
            missing_in_cointracking=[self.tx_ex],
            missing_in_exchange=[self.tx_ct],
            discrepancies=[self.disc],
        )
        self.formatter = ReportFormatter(self.report)

    def test_to_json_valid_schema(self):
        json_str = self.formatter.to_json()
        data = json.loads(json_str)

        self.assertEqual(data["exchange"], "Coinbase")
        self.assertEqual(data["cointracking_file"], "cointracking.csv")
        self.assertEqual(data["summary"]["total_cointracking_records"], 2)
        self.assertEqual(data["summary"]["cointracking_duplicate_groups"], 1)
        self.assertEqual(data["summary"]["missing_in_cointracking"], 1)
        self.assertEqual(data["summary"]["missing_in_exchange"], 1)
        self.assertEqual(len(data["discrepancies"]), 1)
        self.assertEqual(data["discrepancies"][0]["type"], "FEE_MISMATCH")

    def test_to_markdown_output(self):
        md = self.formatter.to_markdown()
        self.assertIn("# CoinTracking vs Coinbase Reconciliation Report", md)
        self.assertIn("## CoinTracking Internal Duplicates", md)
        self.assertIn("## Missing in CoinTracking", md)
        self.assertIn("## Missing in Exchange", md)
        self.assertIn("## Discrepancies and Inconsistencies", md)
        self.assertIn("Fee missing in CT", md)

    def test_print_plain_console(self):
        old_stdout = sys.stdout
        captured = io.StringIO()
        try:
            sys.stdout = captured
            self.formatter._print_plain_console()
            output = captured.getvalue()
            self.assertIn("CoinTracking vs COINBASE Reconciliation Report", output)
            self.assertIn("COINTRACKING INTERNAL DUPLICATES", output)
            self.assertIn("MISSING IN COINTRACKING", output)
        finally:
            sys.stdout = old_stdout

    def test_print_rich_console(self):
        # Ensure _print_rich_console executes without error
        try:
            self.formatter._print_rich_console()
        except Exception as e:
            self.fail(f"_print_rich_console failed with: {e}")


if __name__ == "__main__":
    unittest.main()

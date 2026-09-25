"""Unit tests for the reconciliation and comparison engine."""

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import unittest

from tax_comparator.comparator import TaxComparator
from tax_comparator.models import DiscrepancyType, NormalizedTransaction, TransactionType
from tax_comparator.parsers.bittrex import BittrexParser
from tax_comparator.parsers.coinbase import CoinbaseParser
from tax_comparator.parsers.cointracking import CoinTrackingParser
from tax_comparator.parsers.gemini import GeminiParser

SAMPLE_DIR = Path(__file__).parent.parent / "sample_data"


class TestTaxComparator(unittest.TestCase):

    def setUp(self):
        self.comparator = TaxComparator(
            time_tolerance_seconds=120,
            amount_tolerance_percent=0.05,
            detect_timezone_offsets=True,
        )

    def test_reconciliation_coinbase(self):
        ct_file = SAMPLE_DIR / "cointracking_sample.csv"
        cb_file = SAMPLE_DIR / "coinbase_retail_sample.csv"

        ct_parser = CoinTrackingParser(filter_exchange="Coinbase")
        cb_parser = CoinbaseParser()

        ct_txs = ct_parser.parse_file(ct_file)
        cb_txs = cb_parser.parse_file(cb_file)

        report = self.comparator.compare(
            cointracking_txs=ct_txs,
            exchange_txs=cb_txs,
            exchange_name="Coinbase",
            ct_file_name=ct_file.name,
            ex_file_name=cb_file.name,
        )

        # 1. Duplicates check in CT
        self.assertEqual(len(report.cointracking_duplicates), 1)
        dup_lines = [tx.source_line for tx in report.cointracking_duplicates[0]]
        self.assertIn(2, dup_lines)
        self.assertIn(3, dup_lines)

        # 2. Missing in CT (SOL trade on exchange)
        self.assertEqual(len(report.missing_in_cointracking), 1)
        self.assertEqual(report.missing_in_cointracking[0].received_currency, "SOL")

        # 3. Missing in Exchange (USDC ghost trade in CT)
        self.assertEqual(len(report.missing_in_exchange), 1)
        self.assertEqual(report.missing_in_exchange[0].received_currency, "USDC")

        # 4. Fee mismatch detected on BTC sell
        fee_discrepancies = [
            d for d in report.discrepancies if d.discrepancy_type == DiscrepancyType.FEE_MISMATCH
        ]
        self.assertGreaterEqual(len(fee_discrepancies), 1)

    def test_timezone_detection_gemini(self):
        ct_file = SAMPLE_DIR / "cointracking_sample.csv"
        gem_file = SAMPLE_DIR / "gemini_sample.csv"

        ct_parser = CoinTrackingParser(filter_exchange="Gemini")
        gem_parser = GeminiParser()

        ct_txs = ct_parser.parse_file(ct_file)
        gem_txs = gem_parser.parse_file(gem_file)

        report = self.comparator.compare(
            cointracking_txs=ct_txs,
            exchange_txs=gem_txs,
            exchange_name="Gemini",
            ct_file_name=ct_file.name,
            ex_file_name=gem_file.name,
        )

        # Matched pairs should include the timezone-shifted trade
        self.assertEqual(len(report.matched_pairs), 2)
        
        # Check that timezone discrepancy was logged
        tz_discrepancies = [
            d for d in report.discrepancies if d.discrepancy_type == DiscrepancyType.TIMEZONE_OFFSET
        ]
        self.assertEqual(len(tz_discrepancies), 1)
        self.assertEqual(tz_discrepancies[0].details.get("offset_hours"), -4)

        # Missing in CT should be the 3rd Gemini trade
        self.assertEqual(len(report.missing_in_cointracking), 1)

    def test_reconciliation_bittrex(self):
        ct_file = SAMPLE_DIR / "cointracking_sample.csv"
        bit_file = SAMPLE_DIR / "bittrex_sample.csv"

        ct_parser = CoinTrackingParser(filter_exchange="Bittrex")
        bit_parser = BittrexParser()

        ct_txs = ct_parser.parse_file(ct_file)
        bit_txs = bit_parser.parse_file(bit_file)

        report = self.comparator.compare(
            cointracking_txs=ct_txs,
            exchange_txs=bit_txs,
            exchange_name="Bittrex",
            ct_file_name=ct_file.name,
            ex_file_name=bit_file.name,
        )

        # Both sample trades match by exact order ID
        self.assertEqual(len(report.matched_pairs), 2)
        self.assertEqual(report.exact_matches_count, 2)
        self.assertEqual(len(report.missing_in_cointracking), 1)  # bit-order-9999


if __name__ == "__main__":
    unittest.main()

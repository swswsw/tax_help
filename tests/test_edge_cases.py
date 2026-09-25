"""Unit tests for edge cases, error conditions, and parser/comparator boundaries."""

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest

from tax_comparator.comparator import TaxComparator
from tax_comparator.models import DiscrepancyType, NormalizedTransaction, TransactionType
from tax_comparator.parsers import get_parser
from tax_comparator.parsers.base import BaseParser


class DummyParser(BaseParser):
    EXCHANGE_NAME = "Dummy"

    @classmethod
    def can_parse(cls, file_path: Path) -> bool:
        return False

    def parse_file(self, file_path: Path):
        return []


class TestEdgeCases(unittest.TestCase):

    def setUp(self):
        self.parser = DummyParser()
        self.comparator = TaxComparator(
            time_tolerance_seconds=120,
            amount_tolerance_percent=0.05,
            detect_timezone_offsets=True,
        )

    def test_decimal_cleaning_edge_cases(self):
        self.assertEqual(self.parser.parse_decimal("(12.50)"), Decimal("12.50"))
        self.assertEqual(self.parser.parse_decimal("$ 1,234.56"), Decimal("1234.56"))
        self.assertEqual(self.parser.parse_decimal("€0.00000001"), Decimal("0.00000001"))
        self.assertEqual(self.parser.parse_decimal("+500"), Decimal("500"))
        self.assertIsNone(self.parser.parse_decimal("N/A"))
        self.assertIsNone(self.parser.parse_decimal("-"))
        self.assertIsNone(self.parser.parse_decimal(""))
        self.assertIsNone(self.parser.parse_decimal(None))
        self.assertIsNone(self.parser.parse_decimal("invalid_number"))

    def test_timestamp_parsing_edge_cases(self):
        # ISO with fractional seconds
        dt1 = self.parser.parse_timestamp("2021-05-10T14:23:05.123456Z")
        self.assertIsNotNone(dt1)
        self.assertEqual(dt1.tzinfo, timezone.utc)

        # US format with 12h AM/PM
        dt2 = self.parser.parse_timestamp("05/10/2021 02:23:05 PM")
        self.assertIsNotNone(dt2)
        self.assertEqual(dt2.hour, 14)

        # Invalid timestamp
        self.assertIsNone(self.parser.parse_timestamp("not a date"))
        self.assertIsNone(self.parser.parse_timestamp(""))
        self.assertIsNone(self.parser.parse_timestamp(None))

    def test_ticker_normalization(self):
        self.assertEqual(self.parser.normalize_currency("xbt"), "BTC")
        self.assertEqual(self.parser.normalize_currency("xdg"), "DOGE")
        self.assertEqual(self.parser.normalize_currency("bchabc"), "BCH")
        self.assertIsNone(self.parser.normalize_currency(""))
        self.assertIsNone(self.parser.normalize_currency(None))

    def test_get_parser_invalid_inputs(self):
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as f:
            f.write("Unknown,Header,One,Two\n1,2,3,4\n")
            tmp_path = Path(f.name)

        try:
            # Unknown exchange string
            with self.assertRaises(ValueError):
                get_parser(exchange_name="non_existent_exchange")

            # Unknown format auto-detect
            with self.assertRaises(ValueError):
                get_parser(file_path=tmp_path)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_exchange_internal_duplicates(self):
        # Two identical transactions in the exchange file
        tx1 = NormalizedTransaction(
            source_id="EX-1",
            source_file="ex.csv",
            source_line=1,
            exchange="Gemini",
            timestamp=datetime(2021, 6, 1, 12, 0, 0, tzinfo=timezone.utc),
            tx_type=TransactionType.BUY,
            received_amount=Decimal("1.0"),
            received_currency="BTC",
            sent_amount=Decimal("30000.00"),
            sent_currency="USD",
            order_id="DUP-ORDER",
        )
        tx2 = NormalizedTransaction(
            source_id="EX-2",
            source_file="ex.csv",
            source_line=2,
            exchange="Gemini",
            timestamp=datetime(2021, 6, 1, 12, 0, 0, tzinfo=timezone.utc),
            tx_type=TransactionType.BUY,
            received_amount=Decimal("1.0"),
            received_currency="BTC",
            sent_amount=Decimal("30000.00"),
            sent_currency="USD",
            order_id="DUP-ORDER",
        )

        report = self.comparator.compare(
            cointracking_txs=[],
            exchange_txs=[tx1, tx2],
            exchange_name="Gemini",
            ct_file_name="ct.csv",
            ex_file_name="ex.csv",
        )

        self.assertEqual(len(report.exchange_duplicates), 1)
        self.assertEqual(len(report.exchange_duplicates[0]), 2)
        ex_dup_discs = [
            d for d in report.discrepancies if d.discrepancy_type == DiscrepancyType.INTERNAL_DUPLICATE_EXCHANGE
        ]
        self.assertEqual(len(ex_dup_discs), 1)

    def test_amount_mismatch_discrepancy(self):
        # CT says 1.0 BTC, but Exchange recorded 0.95 BTC (outside tolerance)
        tx_ct = NormalizedTransaction(
            source_id="CT-1",
            source_file="ct.csv",
            source_line=1,
            exchange="Coinbase",
            timestamp=datetime(2021, 5, 1, 10, 0, 0, tzinfo=timezone.utc),
            tx_type=TransactionType.BUY,
            received_amount=Decimal("1.0"),
            received_currency="BTC",
            sent_amount=Decimal("50000.00"),
            sent_currency="USD",
            order_id="ID-MISMATCH-AMT",
        )
        tx_ex = NormalizedTransaction(
            source_id="EX-1",
            source_file="ex.csv",
            source_line=1,
            exchange="Coinbase",
            timestamp=datetime(2021, 5, 1, 10, 0, 0, tzinfo=timezone.utc),
            tx_type=TransactionType.BUY,
            received_amount=Decimal("0.95"),  # 5% difference
            received_currency="BTC",
            sent_amount=Decimal("50000.00"),
            sent_currency="USD",
            order_id="ID-MISMATCH-AMT",
        )

        report = self.comparator.compare(
            cointracking_txs=[tx_ct],
            exchange_txs=[tx_ex],
            exchange_name="Coinbase",
            ct_file_name="ct.csv",
            ex_file_name="ex.csv",
        )

        self.assertEqual(len(report.matched_pairs), 1)
        amount_discs = [
            d for d in report.discrepancies if d.discrepancy_type == DiscrepancyType.AMOUNT_MISMATCH
        ]
        self.assertEqual(len(amount_discs), 1)
        self.assertIn("Received amount mismatch", amount_discs[0].message)

    def test_timestamp_drift_discrepancy(self):
        # Matches by exact ID, but timestamps are 45 seconds apart (drift > 15s)
        tx_ct = NormalizedTransaction(
            source_id="CT-1",
            source_file="ct.csv",
            source_line=1,
            exchange="Coinbase",
            timestamp=datetime(2021, 5, 1, 10, 0, 0, tzinfo=timezone.utc),
            tx_type=TransactionType.BUY,
            received_amount=Decimal("1.0"),
            received_currency="BTC",
            sent_amount=Decimal("50000.00"),
            sent_currency="USD",
            order_id="ID-DRIFT",
        )
        tx_ex = NormalizedTransaction(
            source_id="EX-1",
            source_file="ex.csv",
            source_line=1,
            exchange="Coinbase",
            timestamp=datetime(2021, 5, 1, 10, 0, 45, tzinfo=timezone.utc),
            tx_type=TransactionType.BUY,
            received_amount=Decimal("1.0"),
            received_currency="BTC",
            sent_amount=Decimal("50000.00"),
            sent_currency="USD",
            order_id="ID-DRIFT",
        )

        report = self.comparator.compare(
            cointracking_txs=[tx_ct],
            exchange_txs=[tx_ex],
            exchange_name="Coinbase",
            ct_file_name="ct.csv",
            ex_file_name="ex.csv",
        )

        self.assertEqual(len(report.matched_pairs), 1)
        drift_discs = [
            d for d in report.discrepancies if d.discrepancy_type == DiscrepancyType.TIMESTAMP_MISMATCH
        ]
        self.assertEqual(len(drift_discs), 1)


if __name__ == "__main__":
    unittest.main()

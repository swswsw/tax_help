"""Tests for advanced comparator logic, tolerance boundaries, tie-breaking, and clean runs."""

from datetime import datetime, timezone
from decimal import Decimal
import unittest

from tax_comparator.comparator import TaxComparator
from tax_comparator.models import NormalizedTransaction, TransactionType


class TestComparatorAdvanced(unittest.TestCase):

    def test_clean_reconciliation_perfect_match(self):
        # Everything matches 100% with no discrepancies, no duplicates, no missing
        t1 = datetime(2021, 6, 1, 10, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2021, 6, 2, 11, 0, 0, tzinfo=timezone.utc)

        ct_tx1 = NormalizedTransaction(
            source_id="CT-1",
            source_file="ct.csv",
            source_line=2,
            exchange="Coinbase",
            timestamp=t1,
            tx_type=TransactionType.BUY,
            received_amount=Decimal("0.5"),
            received_currency="BTC",
            sent_amount=Decimal("15000.00"),
            sent_currency="USD",
            fee_amount=Decimal("15.00"),
            fee_currency="USD",
            order_id="ORD-1",
        )
        ct_tx2 = NormalizedTransaction(
            source_id="CT-2",
            source_file="ct.csv",
            source_line=3,
            exchange="Coinbase",
            timestamp=t2,
            tx_type=TransactionType.SELL,
            received_amount=Decimal("16000.00"),
            received_currency="USD",
            sent_amount=Decimal("0.5"),
            sent_currency="BTC",
            fee_amount=Decimal("16.00"),
            fee_currency="USD",
            order_id="ORD-2",
        )

        ex_tx1 = NormalizedTransaction(
            source_id="EX-1",
            source_file="ex.csv",
            source_line=10,
            exchange="Coinbase",
            timestamp=t1,
            tx_type=TransactionType.BUY,
            received_amount=Decimal("0.5"),
            received_currency="BTC",
            sent_amount=Decimal("15000.00"),
            sent_currency="USD",
            fee_amount=Decimal("15.00"),
            fee_currency="USD",
            order_id="ORD-1",
        )
        ex_tx2 = NormalizedTransaction(
            source_id="EX-2",
            source_file="ex.csv",
            source_line=11,
            exchange="Coinbase",
            timestamp=t2,
            tx_type=TransactionType.SELL,
            received_amount=Decimal("16000.00"),
            received_currency="USD",
            sent_amount=Decimal("0.5"),
            sent_currency="BTC",
            fee_amount=Decimal("16.00"),
            fee_currency="USD",
            order_id="ORD-2",
        )

        comparator = TaxComparator()
        report = comparator.compare(
            cointracking_txs=[ct_tx1, ct_tx2],
            exchange_txs=[ex_tx1, ex_tx2],
            exchange_name="Coinbase",
            ct_file_name="ct.csv",
            ex_file_name="ex.csv",
        )

        self.assertEqual(report.exact_matches_count, 2)
        self.assertEqual(report.matched_with_discrepancies_count, 0)
        self.assertEqual(len(report.cointracking_duplicates), 0)
        self.assertEqual(len(report.exchange_duplicates), 0)
        self.assertEqual(len(report.missing_in_cointracking), 0)
        self.assertEqual(len(report.missing_in_exchange), 0)
        self.assertEqual(len(report.discrepancies), 0)

    def test_amount_tolerance_boundary_conditions(self):
        # Base amount: 10000.00 USD
        # 0.05% tolerance = $5.00
        # Diff of $4.00 (0.04%) should MATCH
        # Diff of $6.00 (0.06%) should NOT MATCH
        t = datetime(2021, 6, 1, 10, 0, 0, tzinfo=timezone.utc)

        ct_tx = NormalizedTransaction(
            source_id="CT-1",
            source_file="ct.csv",
            source_line=2,
            exchange="Coinbase",
            timestamp=t,
            tx_type=TransactionType.BUY,
            received_amount=Decimal("1.0"),
            received_currency="BTC",
            sent_amount=Decimal("10000.00"),
            sent_currency="USD",
            order_id=None,
        )

        # 0.04% diff: 10004.00 USD
        ex_tx_within = NormalizedTransaction(
            source_id="EX-1",
            source_file="ex.csv",
            source_line=2,
            exchange="Coinbase",
            timestamp=t,
            tx_type=TransactionType.BUY,
            received_amount=Decimal("1.0"),
            received_currency="BTC",
            sent_amount=Decimal("10004.00"),
            sent_currency="USD",
            order_id=None,
        )

        comp_default = TaxComparator(amount_tolerance_percent=0.05)
        report_within = comp_default.compare([ct_tx], [ex_tx_within], "Coinbase", "ct.csv", "ex.csv")
        self.assertEqual(len(report_within.matched_pairs), 1)

        # 0.06% diff: 10006.00 USD
        ex_tx_outside = NormalizedTransaction(
            source_id="EX-2",
            source_file="ex.csv",
            source_line=3,
            exchange="Coinbase",
            timestamp=t,
            tx_type=TransactionType.BUY,
            received_amount=Decimal("1.0"),
            received_currency="BTC",
            sent_amount=Decimal("10006.00"),
            sent_currency="USD",
            order_id=None,
        )
        report_outside = comp_default.compare([ct_tx], [ex_tx_outside], "Coinbase", "ct.csv", "ex.csv")
        self.assertEqual(len(report_outside.matched_pairs), 0)
        self.assertEqual(len(report_outside.missing_in_cointracking), 1)
        self.assertEqual(len(report_outside.missing_in_exchange), 1)

    def test_time_tolerance_boundary_conditions(self):
        # Time tolerance: 120 seconds
        t_base = datetime(2021, 6, 1, 10, 0, 0, tzinfo=timezone.utc)
        t_within = datetime(2021, 6, 1, 10, 1, 40, tzinfo=timezone.utc)   # 100s later
        t_outside = datetime(2021, 6, 1, 10, 2, 25, tzinfo=timezone.utc)  # 145s later

        ct_tx = NormalizedTransaction(
            source_id="CT-1",
            source_file="ct.csv",
            source_line=2,
            exchange="Gemini",
            timestamp=t_base,
            tx_type=TransactionType.BUY,
            received_amount=Decimal("1.0"),
            received_currency="BTC",
            sent_amount=Decimal("30000.00"),
            sent_currency="USD",
        )

        ex_within = NormalizedTransaction(
            source_id="EX-1",
            source_file="ex.csv",
            source_line=2,
            exchange="Gemini",
            timestamp=t_within,
            tx_type=TransactionType.BUY,
            received_amount=Decimal("1.0"),
            received_currency="BTC",
            sent_amount=Decimal("30000.00"),
            sent_currency="USD",
        )

        comparator = TaxComparator(time_tolerance_seconds=120)
        report1 = comparator.compare([ct_tx], [ex_within], "Gemini", "ct.csv", "ex.csv")
        self.assertEqual(len(report1.matched_pairs), 1)

        ex_outside = NormalizedTransaction(
            source_id="EX-2",
            source_file="ex.csv",
            source_line=3,
            exchange="Gemini",
            timestamp=t_outside,
            tx_type=TransactionType.BUY,
            received_amount=Decimal("1.0"),
            received_currency="BTC",
            sent_amount=Decimal("30000.00"),
            sent_currency="USD",
        )
        report2 = comparator.compare([ct_tx], [ex_outside], "Gemini", "ct.csv", "ex.csv")
        self.assertEqual(len(report2.matched_pairs), 0)

    def test_timezone_detection_disabled_flag(self):
        # Shifted by exactly 4 hours (e.g. EDT to UTC)
        t_ct = datetime(2021, 5, 15, 14, 0, 0, tzinfo=timezone.utc)
        t_ex = datetime(2021, 5, 15, 18, 0, 0, tzinfo=timezone.utc)

        ct_tx = NormalizedTransaction(
            source_id="CT-1",
            source_file="ct.csv",
            source_line=2,
            exchange="Gemini",
            timestamp=t_ct,
            tx_type=TransactionType.BUY,
            received_amount=Decimal("2.0"),
            received_currency="ETH",
            sent_amount=Decimal("5000.00"),
            sent_currency="USD",
        )
        ex_tx = NormalizedTransaction(
            source_id="EX-1",
            source_file="ex.csv",
            source_line=2,
            exchange="Gemini",
            timestamp=t_ex,
            tx_type=TransactionType.BUY,
            received_amount=Decimal("2.0"),
            received_currency="ETH",
            sent_amount=Decimal("5000.00"),
            sent_currency="USD",
        )

        # When detect_timezone_offsets is False, it should NOT match
        comp_no_tz = TaxComparator(detect_timezone_offsets=False)
        report_no_tz = comp_no_tz.compare([ct_tx], [ex_tx], "Gemini", "ct.csv", "ex.csv")
        self.assertEqual(len(report_no_tz.matched_pairs), 0)
        self.assertEqual(len(report_no_tz.missing_in_cointracking), 1)

        # When detect_timezone_offsets is True, it SHOULD match with TIMEZONE_OFFSET discrepancy
        comp_with_tz = TaxComparator(detect_timezone_offsets=True)
        report_tz = comp_with_tz.compare([ct_tx], [ex_tx], "Gemini", "ct.csv", "ex.csv")
        self.assertEqual(len(report_tz.matched_pairs), 1)
        self.assertEqual(report_tz.matched_pairs[0].match_method, "TIMEZONE_ADJUSTED")

    def test_closest_timestamp_tie_breaker(self):
        # One CT trade at 12:00:00
        # Two matching exchange trades at 12:00:10 (10s) and 12:00:50 (50s)
        t_base = datetime(2021, 7, 1, 12, 0, 0, tzinfo=timezone.utc)
        t_close = datetime(2021, 7, 1, 12, 0, 10, tzinfo=timezone.utc)
        t_far = datetime(2021, 7, 1, 12, 0, 50, tzinfo=timezone.utc)

        ct_tx = NormalizedTransaction(
            source_id="CT-1",
            source_file="ct.csv",
            source_line=2,
            exchange="Bittrex",
            timestamp=t_base,
            tx_type=TransactionType.BUY,
            received_amount=Decimal("50.0"),
            received_currency="ADA",
            sent_amount=Decimal("75.00"),
            sent_currency="USD",
        )
        ex_far = NormalizedTransaction(
            source_id="EX-FAR",
            source_file="ex.csv",
            source_line=2,
            exchange="Bittrex",
            timestamp=t_far,
            tx_type=TransactionType.BUY,
            received_amount=Decimal("50.0"),
            received_currency="ADA",
            sent_amount=Decimal("75.00"),
            sent_currency="USD",
        )
        ex_close = NormalizedTransaction(
            source_id="EX-CLOSE",
            source_file="ex.csv",
            source_line=3,
            exchange="Bittrex",
            timestamp=t_close,
            tx_type=TransactionType.BUY,
            received_amount=Decimal("50.0"),
            received_currency="ADA",
            sent_amount=Decimal("75.00"),
            sent_currency="USD",
        )

        comparator = TaxComparator(time_tolerance_seconds=120)
        # Put far first in exchange list
        report = comparator.compare([ct_tx], [ex_far, ex_close], "Bittrex", "ct.csv", "ex.csv")

        self.assertEqual(len(report.matched_pairs), 1)
        # Should match EX-CLOSE because |12:00:10 - 12:00:00| = 10s < 50s
        self.assertEqual(report.matched_pairs[0].exchange_tx.source_id, "EX-CLOSE")
        self.assertEqual(report.matched_pairs[0].time_diff_seconds, 10.0)

    def test_crypto_to_crypto_trade_matching(self):
        # Direct crypto-to-crypto trade: Sell ETH to receive BTC
        t = datetime(2021, 8, 1, 15, 0, 0, tzinfo=timezone.utc)

        ct_tx = NormalizedTransaction(
            source_id="CT-1",
            source_file="ct.csv",
            source_line=5,
            exchange="Bittrex",
            timestamp=t,
            tx_type=TransactionType.TRADE,
            received_amount=Decimal("0.15000000"),
            received_currency="BTC",
            sent_amount=Decimal("2.50000000"),
            sent_currency="ETH",
            fee_amount=Decimal("0.00030000"),
            fee_currency="BTC",
        )
        ex_tx = NormalizedTransaction(
            source_id="EX-1",
            source_file="ex.csv",
            source_line=8,
            exchange="Bittrex",
            timestamp=t,
            tx_type=TransactionType.TRADE,
            received_amount=Decimal("0.15000000"),
            received_currency="BTC",
            sent_amount=Decimal("2.50000000"),
            sent_currency="ETH",
            fee_amount=Decimal("0.00030000"),
            fee_currency="BTC",
        )

        comparator = TaxComparator()
        report = comparator.compare([ct_tx], [ex_tx], "Bittrex", "ct.csv", "ex.csv")
        self.assertEqual(len(report.matched_pairs), 1)
        self.assertEqual(report.exact_matches_count, 1)


if __name__ == "__main__":
    unittest.main()

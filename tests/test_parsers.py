"""Unit tests for CoinTracking and Exchange CSV parsers."""

from decimal import Decimal
from pathlib import Path
import unittest

from tax_comparator.models import TransactionType
from tax_comparator.parsers.base import BaseParser
from tax_comparator.parsers.bittrex import BittrexParser
from tax_comparator.parsers.coinbase import CoinbaseParser
from tax_comparator.parsers.cointracking import CoinTrackingParser
from tax_comparator.parsers.gemini import GeminiParser

SAMPLE_DIR = Path(__file__).parent.parent / "sample_data"


class TestParsers(unittest.TestCase):

    def test_base_parser_helpers(self):
        # Timestamp parsing
        dt1 = BaseParser.parse_timestamp("2021-05-10T14:23:05Z")
        self.assertIsNotNone(dt1)
        self.assertEqual(dt1.year, 2021)
        self.assertEqual(dt1.month, 5)
        self.assertEqual(dt1.hour, 14)

        dt2 = BaseParser.parse_timestamp("7/20/2021 6:45:12 PM")
        self.assertIsNotNone(dt2)
        self.assertEqual(dt2.hour, 18)
        self.assertEqual(dt2.minute, 45)

        # Decimal parsing
        self.assertEqual(BaseParser.parse_decimal("$4,500.50"), Decimal("4500.50"))
        self.assertEqual(BaseParser.parse_decimal("-$15.00"), Decimal("15.00"))
        self.assertIsNone(BaseParser.parse_decimal(""))
        self.assertIsNone(BaseParser.parse_decimal("null"))

        # Currency normalization
        self.assertEqual(BaseParser.normalize_currency("xbt"), "BTC")
        self.assertEqual(BaseParser.normalize_currency("eth"), "ETH")
        self.assertEqual(BaseParser.normalize_currency("USD"), "USD")

    def test_cointracking_parser(self):
        ct_file = SAMPLE_DIR / "cointracking_sample.csv"
        self.assertTrue(CoinTrackingParser.can_parse(ct_file))

        # Parse all
        parser = CoinTrackingParser()
        all_txs = parser.parse_file(ct_file)
        self.assertEqual(len(all_txs), 10)

        # Parse filtered by Coinbase
        cb_parser = CoinTrackingParser(filter_exchange="Coinbase")
        cb_txs = cb_parser.parse_file(ct_file)
        self.assertEqual(len(cb_txs), 6)

        first = cb_txs[0]
        self.assertEqual(first.tx_type, TransactionType.BUY)
        self.assertEqual(first.received_amount, Decimal("1.50000000"))
        self.assertEqual(first.received_currency, "ETH")
        self.assertEqual(first.sent_amount, Decimal("4500.00"))
        self.assertEqual(first.sent_currency, "USD")
        self.assertEqual(first.fee_amount, Decimal("15.00"))
        self.assertEqual(first.order_id, "CB-TR-1001")

        # Deposit check
        deposit = [t for t in cb_txs if t.tx_type == TransactionType.DEPOSIT][0]
        self.assertEqual(deposit.received_amount, Decimal("5000.00"))
        self.assertEqual(deposit.received_currency, "USD")
        self.assertIsNone(deposit.sent_amount)

        # Withdrawal check
        withdrawal = [t for t in cb_txs if t.tx_type == TransactionType.WITHDRAWAL][0]
        self.assertEqual(withdrawal.sent_amount, Decimal("0.50000000"))
        self.assertEqual(withdrawal.sent_currency, "ETH")
        self.assertIsNone(withdrawal.received_amount)

    def test_coinbase_retail_parser(self):
        cb_file = SAMPLE_DIR / "coinbase_retail_sample.csv"
        self.assertTrue(CoinbaseParser.can_parse(cb_file))

        parser = CoinbaseParser()
        txs = parser.parse_file(cb_file)
        self.assertEqual(len(txs), 5)

        first = txs[0]
        self.assertEqual(first.tx_type, TransactionType.BUY)
        self.assertEqual(first.received_amount, Decimal("1.5"))
        self.assertEqual(first.received_currency, "ETH")
        self.assertEqual(first.sent_amount, Decimal("4500.00"))
        self.assertEqual(first.sent_currency, "USD")
        self.assertEqual(first.fee_amount, Decimal("15.00"))

    def test_coinbase_pro_parser(self):
        cb_pro_file = SAMPLE_DIR / "coinbase_pro_sample.csv"
        self.assertTrue(CoinbaseParser.can_parse(cb_pro_file))

        parser = CoinbaseParser()
        txs = parser.parse_file(cb_pro_file)
        self.assertEqual(len(txs), 2)

        first = txs[0]
        self.assertEqual(first.tx_type, TransactionType.BUY)
        self.assertEqual(first.order_id, "CB-TR-1001")
        self.assertEqual(first.received_amount, Decimal("1.5"))
        self.assertEqual(first.received_currency, "ETH")
        self.assertEqual(first.fee_amount, Decimal("15.00"))

    def test_gemini_parser(self):
        gem_file = SAMPLE_DIR / "gemini_sample.csv"
        self.assertTrue(GeminiParser.can_parse(gem_file))

        parser = GeminiParser()
        txs = parser.parse_file(gem_file)
        self.assertEqual(len(txs), 3)

        buy_tx = txs[0]
        self.assertEqual(buy_tx.tx_type, TransactionType.BUY)
        self.assertEqual(buy_tx.received_amount, Decimal("0.10000000"))
        self.assertEqual(buy_tx.received_currency, "BTC")
        self.assertEqual(buy_tx.sent_amount, Decimal("3200.00"))
        self.assertEqual(buy_tx.sent_currency, "USD")
        self.assertEqual(buy_tx.fee_amount, Decimal("11.20"))

        sell_tx = txs[1]
        self.assertEqual(sell_tx.tx_type, TransactionType.SELL)
        self.assertEqual(sell_tx.received_amount, Decimal("7000.00"))
        self.assertEqual(sell_tx.received_currency, "USD")
        self.assertEqual(sell_tx.sent_amount, Decimal("2.00000000"))
        self.assertEqual(sell_tx.sent_currency, "ETH")

    def test_bittrex_parser(self):
        bit_file = SAMPLE_DIR / "bittrex_sample.csv"
        self.assertTrue(BittrexParser.can_parse(bit_file))

        parser = BittrexParser()
        txs = parser.parse_file(bit_file)
        self.assertEqual(len(txs), 3)

        first = txs[0]
        self.assertEqual(first.order_id, "bit-order-5544")
        self.assertEqual(first.tx_type, TransactionType.BUY)
        # Market BTC-LTC -> base: LTC, quote: BTC
        self.assertEqual(first.received_amount, Decimal("2.50000000"))
        self.assertEqual(first.received_currency, "LTC")
        self.assertEqual(first.sent_amount, Decimal("0.01500000"))
        self.assertEqual(first.sent_currency, "BTC")
        self.assertEqual(first.fee_amount, Decimal("0.00003750"))


if __name__ == "__main__":
    unittest.main()

"""Tests for parser robustness: BOM headers, CRLF line endings, transfers, and varied formats."""

from decimal import Decimal
from pathlib import Path
import tempfile
import unittest

from tax_comparator.models import TransactionType
from tax_comparator.parsers.bittrex import BittrexParser
from tax_comparator.parsers.coinbase import CoinbaseParser
from tax_comparator.parsers.cointracking import CoinTrackingParser
from tax_comparator.parsers.gemini import GeminiParser


class TestParserRobustness(unittest.TestCase):

    def test_utf8_bom_and_crlf_handling(self):
        # File with UTF-8 BOM (\ufeff) and Windows CRLF line endings (\r\n)
        content = (
            "\"Type\",\"Buy\",\"Cur.\",\"Sell\",\"Cur.\",\"Fee\",\"Cur.\",\"Exchange\",\"Group\",\"Comment\",\"Date\",\"Tx-ID\"\r\n"
            "\"Trade\",\"1.00000000\",\"BTC\",\"30000.00\",\"USD\",\"15.00\",\"USD\",\"Coinbase\",\"\",\"Windows export\",\"2021-05-10 14:00:00\",\"WIN-1\"\r\n"
        )
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="wb", delete=False) as f:
            f.write(content.encode("utf-8-sig"))
            tmp_path = Path(f.name)

        try:
            parser = CoinTrackingParser(filter_exchange="Coinbase")
            txs = parser.parse_file(tmp_path)
            self.assertEqual(len(txs), 1)
            self.assertEqual(txs[0].order_id, "WIN-1")
            self.assertEqual(txs[0].received_amount, Decimal("1.0"))
            self.assertEqual(txs[0].received_currency, "BTC")
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_cointracking_transaction_types(self):
        # Diverse transaction types: Income, Staking, Mining, Spend, Gift
        csv_text = """Type,Buy,Cur.,Sell,Cur.,Fee,Cur.,Exchange,Group,Comment,Date,Tx-ID
Income,50.00,USD,,,0.00,USD,Coinbase,,Referral bonus,2021-01-01 10:00:00,INC-1
Mining,0.005,BTC,,,0.00,USD,Coinbase,,Mining payout,2021-02-01 10:00:00,MIN-1
Staking,1.25,ETH,,,0.00,USD,Coinbase,,ETH2 rewards,2021-03-01 10:00:00,STK-1
Spend,,,25.00,USDC,0.00,USD,Coinbase,,Bought coffee,2021-04-01 10:00:00,SPD-1
Gift,100.00,DOGE,,,0.00,USD,Coinbase,,DOGE gift,2021-05-01 10:00:00,GFT-1
"""
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", encoding="utf-8", delete=False) as f:
            f.write(csv_text)
            tmp_path = Path(f.name)

        try:
            parser = CoinTrackingParser(filter_exchange="Coinbase")
            txs = parser.parse_file(tmp_path)
            self.assertEqual(len(txs), 5)
            self.assertEqual(txs[0].tx_type, TransactionType.INCOME)
            self.assertEqual(txs[1].tx_type, TransactionType.INCOME)
            self.assertEqual(txs[2].tx_type, TransactionType.INCOME)
            self.assertEqual(txs[3].tx_type, TransactionType.OTHER)
            self.assertEqual(txs[4].tx_type, TransactionType.OTHER)
            self.assertEqual(txs[3].sent_amount, Decimal("25.00"))
            self.assertEqual(txs[4].received_amount, Decimal("100.00"))
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_cointracking_exchange_filter(self):
        csv_text = """Type,Buy,Cur.,Sell,Cur.,Fee,Cur.,Exchange,Group,Comment,Date,Tx-ID
Trade,1.0,BTC,50000.00,USD,10.00,USD,Coinbase,,Coinbase buy,2021-05-01 12:00:00,CB-1
Trade,2.0,ETH,6000.00,USD,5.00,USD,Gemini,,Gemini buy,2021-05-02 12:00:00,GEM-1
Trade,10.0,LTC,1500.00,USD,2.00,USD,Bittrex,,Bittrex buy,2021-05-03 12:00:00,BIT-1
"""
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", encoding="utf-8", delete=False) as f:
            f.write(csv_text)
            tmp_path = Path(f.name)

        try:
            # Filter specifically for Gemini
            parser_gem = CoinTrackingParser(filter_exchange="Gemini")
            gem_txs = parser_gem.parse_file(tmp_path)
            self.assertEqual(len(gem_txs), 1)
            self.assertEqual(gem_txs[0].order_id, "GEM-1")

            # No filter should return all 3
            parser_all = CoinTrackingParser(filter_exchange=None)
            all_txs = parser_all.parse_file(tmp_path)
            self.assertEqual(len(all_txs), 3)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_gemini_transfer_history_format(self):
        # Gemini transfer history CSV (deposits and withdrawals)
        csv_text = """Date,Time (UTC),Type,Symbol,Specification,Amount,Fee,USD Amount
2021-03-01,10:00:00,Deposit,BTC,Crypto Deposit,0.50000000,0.00000000,$24000.00
2021-03-15,15:30:00,Withdrawal,USD,Wire Withdrawal,5000.00,0.00,$5000.00
"""
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", encoding="utf-8", delete=False) as f:
            f.write(csv_text)
            tmp_path = Path(f.name)

        try:
            parser = GeminiParser()
            self.assertTrue(GeminiParser.can_parse(tmp_path))
            txs = parser.parse_file(tmp_path)
            self.assertEqual(len(txs), 2)

            dep = txs[0]
            self.assertEqual(dep.tx_type, TransactionType.DEPOSIT)
            self.assertEqual(dep.received_amount, Decimal("0.50000000"))
            self.assertEqual(dep.received_currency, "BTC")

            wth = txs[1]
            self.assertEqual(wth.tx_type, TransactionType.WITHDRAWAL)
            self.assertEqual(wth.sent_amount, Decimal("5000.00"))
            self.assertEqual(wth.sent_currency, "USD")
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_bittrex_transfer_history_format(self):
        # Bittrex deposits and withdrawals CSV
        csv_text = """PaymentUuid,Currency,Amount,Address,Opened,Authorized,Pending,Completed,TxCost,TxId
pay-uuid-001,BTC,0.25000000,1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa,2021-04-01T12:00:00,True,False,2021-04-01T12:15:00,0.00050000,0xtxid123
pay-uuid-002,USD,1000.00,wire_acct_456,2021-04-05T09:00:00,True,False,2021-04-05T09:30:00,0.00,ACH-456
"""
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", encoding="utf-8", delete=False) as f:
            f.write(csv_text)
            tmp_path = Path(f.name)

        try:
            parser = BittrexParser()
            self.assertTrue(BittrexParser.can_parse(tmp_path))
            txs = parser.parse_file(tmp_path)
            self.assertEqual(len(txs), 2)

            tx1 = txs[0]
            self.assertEqual(tx1.tx_type, TransactionType.WITHDRAWAL)
            self.assertEqual(tx1.sent_amount, Decimal("0.25000000"))
            self.assertEqual(tx1.sent_currency, "BTC")
            self.assertEqual(tx1.fee_amount, Decimal("0.00050000"))
            self.assertEqual(tx1.fee_currency, "BTC")
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_coinbase_varying_preamble_lengths(self):
        # Only 2 preamble lines before header
        short_preamble = """Coinbase Report
User: Alice
Timestamp,Transaction Type,Asset,Quantity Transacted,Spot Price Currency,Spot Price at Transaction,Subtotal,Total (inclusive of fees and/or spread),Fees and/or Spread,Notes
2021-07-01T12:00:00Z,Buy,BTC,0.01,USD,35000.00,350.00,355.00,5.00,Bought 0.01 BTC
"""
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", encoding="utf-8", delete=False) as f:
            f.write(short_preamble)
            tmp_path = Path(f.name)

        try:
            parser = CoinbaseParser()
            self.assertTrue(CoinbaseParser.can_parse(tmp_path))
            txs = parser.parse_file(tmp_path)
            self.assertEqual(len(txs), 1)
            self.assertEqual(txs[0].received_amount, Decimal("0.01"))
            self.assertEqual(txs[0].fee_amount, Decimal("5.00"))
        finally:
            if tmp_path.exists():
                tmp_path.unlink()


if __name__ == "__main__":
    unittest.main()

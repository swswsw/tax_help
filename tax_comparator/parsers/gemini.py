"""Parser for Gemini ActiveTrader and Account Transaction history exports."""

import csv
from decimal import Decimal
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

from tax_comparator.models import NormalizedTransaction, TransactionType
from tax_comparator.parsers.base import BaseParser


class GeminiParser(BaseParser):
    """Parses Gemini Order History (ActiveTrader) and Account Transfer CSV reports."""

    EXCHANGE_NAME = "Gemini"

    @classmethod
    def can_parse(cls, file_path: Path) -> bool:
        try:
            with open(file_path, mode="r", encoding="utf-8-sig") as f:
                for _ in range(5):
                    line = f.readline().lower()
                    if not line:
                        break
                    # Typical Gemini headers
                    if ("time (utc)" in line or "time" in line) and "symbol" in line and (
                        "trading fee" in line or "net proceeds" in line or "liquidity indicator" in line or "specification" in line
                    ):
                        return True
                    if "symbol" in line and "type" in line and ("amount" in line or "btc amount" in line or "usd amount" in line):
                        return True
        except Exception:
            return False
        return False

    def parse_file(self, file_path: Path) -> List[NormalizedTransaction]:
        transactions: List[NormalizedTransaction] = []
        with open(file_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            header: Optional[List[str]] = None
            col_map: Dict[str, int] = {}
            crypto_amt_col: Optional[int] = None
            crypto_asset_from_header: Optional[str] = None
            line_num = 0

            for row in reader:
                line_num += 1
                if not row or not any(field.strip() for field in row):
                    continue

                cleaned_row = [self.clean_string(cell) for cell in row]

                # Seek header row
                if header is None:
                    lower_row = [c.lower() for c in cleaned_row]
                    if any("symbol" in c for c in lower_row) and any("type" in c for c in lower_row):
                        header = cleaned_row
                        col_map = {c.lower(): idx for idx, c in enumerate(cleaned_row)}
                        
                        # Find crypto amount column (e.g. "BTC Amount", "ETH Amount", or generic "Amount")
                        for idx, col in enumerate(cleaned_row):
                            c_low = col.lower()
                            if "amount" in c_low and "usd" not in c_low and "fee" not in c_low:
                                crypto_amt_col = idx
                                m = re.match(r"^([a-z0-9]+)\s+amount", c_low)
                                if m:
                                    crypto_asset_from_header = m.group(1).upper()
                                break
                        continue
                    else:
                        continue

                # Parse data row
                tx = self._parse_row(cleaned_row, col_map, crypto_amt_col, crypto_asset_from_header, file_path, line_num)
                if tx:
                    transactions.append(tx)

        return transactions

    def _parse_row(
        self,
        row: List[str],
        col_map: Dict[str, int],
        crypto_amt_col: Optional[int],
        crypto_asset_from_header: Optional[str],
        file_path: Path,
        line_num: int,
    ) -> Optional[NormalizedTransaction]:
        def get_val(key_sub: str, exclude: Optional[str] = None) -> str:
            # Exact match first
            for k, idx in col_map.items():
                if k == key_sub and idx < len(row):
                    return row[idx]
            # Substring match with exclusion
            for k, idx in col_map.items():
                if key_sub in k and idx < len(row):
                    if exclude and exclude in k:
                        continue
                    return row[idx]
            return ""

        # Extract timestamp
        date_str = get_val("date")
        time_str = get_val("time")
        full_dt_str = f"{date_str} {time_str}".strip() if time_str else date_str
        timestamp = self.parse_timestamp(full_dt_str)
        if not timestamp:
            return None

        tx_type_raw = get_val("type").lower()
        symbol = get_val("symbol").upper()  # e.g. BTCUSD or ETHUSD
        usd_amount = self.parse_decimal(get_val("usd amount") or get_val("net proceeds") or get_val("price"))
        fee = self.parse_decimal(
            get_val("trading fee (usd)") or get_val("trading fee", exclude="rate") or get_val("fee", exclude="rate")
        )
        fee_curr = self.normalize_currency(get_val("fee currency") or "USD")

        # Determine base and quote currency
        quote_curr = "USD"
        base_curr = crypto_asset_from_header
        if symbol.endswith("USD"):
            base_curr = symbol[:-3]
            quote_curr = "USD"
        elif symbol.endswith("EUR"):
            base_curr = symbol[:-3]
            quote_curr = "EUR"
        elif symbol.endswith("GBP"):
            base_curr = symbol[:-3]
            quote_curr = "GBP"
        elif symbol.endswith("BTC") and len(symbol) > 3:
            base_curr = symbol[:-3]
            quote_curr = "BTC"
        elif not base_curr and symbol:
            base_curr = symbol

        base_curr = self.normalize_currency(base_curr)

        # Get crypto amount
        crypto_amount: Optional[Decimal] = None
        if crypto_amt_col is not None and crypto_amt_col < len(row):
            crypto_amount = self.parse_decimal(row[crypto_amt_col])
        if not crypto_amount:
            crypto_amount = self.parse_decimal(get_val("amount"))

        # Determine transaction legs and types
        received_amount: Optional[Decimal] = None
        received_curr: Optional[str] = None
        sent_amount: Optional[Decimal] = None
        sent_curr: Optional[str] = None
        tx_type = TransactionType.OTHER

        if "buy" in tx_type_raw:
            tx_type = TransactionType.BUY
            received_amount = crypto_amount
            received_curr = base_curr
            sent_amount = usd_amount
            sent_curr = quote_curr
        elif "sell" in tx_type_raw:
            tx_type = TransactionType.SELL
            received_amount = usd_amount
            received_curr = quote_curr
            sent_amount = crypto_amount
            sent_curr = base_curr
        elif "deposit" in tx_type_raw or "credit" in tx_type_raw:
            tx_type = TransactionType.DEPOSIT
            received_amount = crypto_amount or usd_amount
            received_curr = base_curr or quote_curr
        elif "withdraw" in tx_type_raw or "debit" in tx_type_raw:
            tx_type = TransactionType.WITHDRAWAL
            sent_amount = crypto_amount or usd_amount
            sent_curr = base_curr or quote_curr

        raw_dict = {f"col_{i}": val for i, val in enumerate(row)}
        for k, v in col_map.items():
            if v < len(row):
                raw_dict[k] = row[v]

        return NormalizedTransaction(
            source_id=f"GEM-{line_num}",
            source_file=file_path.name,
            source_line=line_num,
            exchange=self.EXCHANGE_NAME,
            timestamp=timestamp,
            tx_type=tx_type,
            received_amount=received_amount,
            received_currency=received_curr,
            sent_amount=sent_amount,
            sent_currency=sent_curr,
            fee_amount=fee if fee and fee > 0 else None,
            fee_currency=fee_curr if fee and fee > 0 else None,
            order_id=get_val("order") or get_val("trade id") or None,
            comment=f"Gemini {symbol} {tx_type_raw.upper()}",
            raw_data=raw_dict,
        )

"""Parser for CoinTracking CSV export files (Trade Table / Custom Exports)."""

import csv
from pathlib import Path
from typing import Any, Dict, List, Optional

from tax_comparator.models import NormalizedTransaction, TransactionType
from tax_comparator.parsers.base import BaseParser


class CoinTrackingParser(BaseParser):
    """Parses CoinTracking Trade Table CSV exports."""

    FIAT_CURRENCIES = {"USD", "EUR", "GBP", "CAD", "AUD", "JPY", "CHF"}

    def __init__(self, filter_exchange: Optional[str] = None):
        self.filter_exchange = filter_exchange.lower() if filter_exchange else None

    @classmethod
    def can_parse(cls, file_path: Path) -> bool:
        """Determines if the CSV matches CoinTracking header structures."""
        try:
            with open(file_path, mode="r", encoding="utf-8-sig") as f:
                for line in f:
                    line_clean = line.strip().lower()
                    if not line_clean:
                        continue
                    # Check for signature columns
                    parts = [p.strip().strip('"').strip("'").lower() for p in line_clean.split(",")]
                    if "type" in parts and ("buy" in parts or "buy amount" in parts) and ("sell" in parts or "sell amount" in parts):
                        return True
                    # Check if line contains exchange and date
                    if "exchange" in parts and "date" in parts and "fee" in parts:
                        return True
                    break
        except Exception:
            return False
        return False

    def parse_file(self, file_path: Path) -> List[NormalizedTransaction]:
        transactions: List[NormalizedTransaction] = []
        with open(file_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            header: Optional[List[str]] = None
            col_map: Dict[str, int] = {}

            line_num = 0
            for row in reader:
                line_num += 1
                if not row or not any(field.strip() for field in row):
                    continue

                cleaned_row = [self.clean_string(cell) for cell in row]

                # Identify header row
                if header is None:
                    lower_row = [c.lower() for c in cleaned_row]
                    if "type" in lower_row and ("buy" in lower_row or "buy amount" in lower_row):
                        header = cleaned_row
                        col_map = self._build_column_mapping(cleaned_row)
                        continue
                    else:
                        continue

                # Process data row
                tx = self._parse_row(cleaned_row, col_map, file_path, line_num)
                if tx:
                    # Filter by exchange if requested
                    if self.filter_exchange:
                        if tx.exchange.lower() != self.filter_exchange and self.filter_exchange not in tx.exchange.lower():
                            continue
                    transactions.append(tx)

        return transactions

    def _build_column_mapping(self, header: List[str]) -> Dict[str, int]:
        mapping: Dict[str, int] = {}
        cur_count = 0
        
        for idx, col in enumerate(header):
            c_low = col.lower()
            if c_low == "type":
                mapping["type"] = idx
            elif c_low in ("buy", "buy amount"):
                mapping["buy"] = idx
            elif c_low in ("sell", "sell amount"):
                mapping["sell"] = idx
            elif c_low in ("fee", "fee amount"):
                mapping["fee"] = idx
            elif c_low in ("exchange",):
                mapping["exchange"] = idx
            elif c_low in ("group", "trade group"):
                mapping["group"] = idx
            elif c_low in ("comment", "notes"):
                mapping["comment"] = idx
            elif c_low in ("date", "trade date", "timestamp"):
                mapping["date"] = idx
            elif c_low in ("tx-id", "txid", "trade id", "id", "order id"):
                mapping["tx_id"] = idx
            elif "cur" in c_low or "currency" in c_low or "coin" in c_low:
                # Handle repeated Cur. headers in standard CoinTracking CSV
                if cur_count == 0:
                    mapping["buy_curr"] = idx
                elif cur_count == 1:
                    mapping["sell_curr"] = idx
                elif cur_count == 2:
                    mapping["fee_curr"] = idx
                cur_count += 1

        # Fallback if specific currency headers exist
        for idx, col in enumerate(header):
            c_low = col.lower()
            if "buy" in c_low and ("cur" in c_low or "asset" in c_low):
                mapping["buy_curr"] = idx
            elif "sell" in c_low and ("cur" in c_low or "asset" in c_low):
                mapping["sell_curr"] = idx
            elif "fee" in c_low and ("cur" in c_low or "asset" in c_low):
                mapping["fee_curr"] = idx

        return mapping

    def _parse_row(
        self, row: List[str], col_map: Dict[str, int], file_path: Path, line_num: int
    ) -> Optional[NormalizedTransaction]:
        def get_val(key: str) -> str:
            idx = col_map.get(key)
            if idx is not None and idx < len(row):
                return row[idx]
            return ""

        raw_type = get_val("type").strip()
        date_str = get_val("date")
        timestamp = self.parse_timestamp(date_str)
        if not timestamp:
            return None

        buy_amount = self.parse_decimal(get_val("buy"))
        buy_curr = self.normalize_currency(get_val("buy_curr"))
        sell_amount = self.parse_decimal(get_val("sell"))
        sell_curr = self.normalize_currency(get_val("sell_curr"))
        fee_amount = self.parse_decimal(get_val("fee"))
        fee_curr = self.normalize_currency(get_val("fee_curr"))
        exchange = get_val("exchange") or "Unknown"
        comment = get_val("comment")
        tx_id = get_val("tx_id")

        # Classify transaction type
        lower_type = raw_type.lower()
        if "deposit" in lower_type:
            tx_type = TransactionType.DEPOSIT
        elif "withdrawal" in lower_type:
            tx_type = TransactionType.WITHDRAWAL
        elif any(k in lower_type for k in ("income", "mining", "staking", "reward", "airdrop")):
            tx_type = TransactionType.INCOME
        elif any(k in lower_type for k in ("spend", "lost", "gift", "donation")):
            tx_type = TransactionType.OTHER
        elif "trade" in lower_type or "buy" in lower_type or "sell" in lower_type:
            if buy_amount and sell_amount:
                # If one leg is fiat, refine to BUY or SELL
                if sell_curr in self.FIAT_CURRENCIES and buy_curr not in self.FIAT_CURRENCIES:
                    tx_type = TransactionType.BUY
                elif buy_curr in self.FIAT_CURRENCIES and sell_curr not in self.FIAT_CURRENCIES:
                    tx_type = TransactionType.SELL
                else:
                    tx_type = TransactionType.TRADE
            elif buy_amount and not sell_amount:
                tx_type = TransactionType.BUY
            elif sell_amount and not buy_amount:
                tx_type = TransactionType.SELL
            else:
                tx_type = TransactionType.TRADE
        else:
            tx_type = TransactionType.OTHER

        raw_dict = {
            f"col_{i}": val for i, val in enumerate(row)
        }
        for k, v in col_map.items():
            if v < len(row):
                raw_dict[k] = row[v]

        return NormalizedTransaction(
            source_id=f"CT-{line_num}",
            source_file=file_path.name,
            source_line=line_num,
            exchange=exchange,
            timestamp=timestamp,
            tx_type=tx_type,
            received_amount=buy_amount,
            received_currency=buy_curr,
            sent_amount=sell_amount,
            sent_currency=sell_curr,
            fee_amount=fee_amount,
            fee_currency=fee_curr,
            order_id=tx_id if tx_id else None,
            comment=comment,
            raw_data=raw_dict,
        )

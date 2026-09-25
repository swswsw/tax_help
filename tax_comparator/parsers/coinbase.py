"""Parser for Coinbase Consumer / Retail reports and Coinbase Pro fills exports."""

import csv
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

from tax_comparator.models import NormalizedTransaction, TransactionType
from tax_comparator.parsers.base import BaseParser


class CoinbaseParser(BaseParser):
    """Parses Coinbase Consumer (Retail) and Coinbase Pro CSV reports."""

    EXCHANGE_NAME = "Coinbase"

    @classmethod
    def can_parse(cls, file_path: Path) -> bool:
        try:
            with open(file_path, mode="r", encoding="utf-8-sig") as f:
                content_preview = ""
                for _ in range(25):
                    line = f.readline()
                    if not line:
                        break
                    content_preview += line.lower()
                    
                # Coinbase Pro check
                if "trade id" in content_preview and "product" in content_preview and "side" in content_preview:
                    return True
                # Coinbase Retail check
                if "timestamp" in content_preview and "transaction type" in content_preview and (
                    "quantity transacted" in content_preview or "spot price" in content_preview
                ):
                    return True
                if "coinbase" in content_preview and ("transaction type" in content_preview or "spot price" in content_preview):
                    return True
        except Exception:
            return False
        return False

    def parse_file(self, file_path: Path) -> List[NormalizedTransaction]:
        is_pro = self._check_if_pro(file_path)
        if is_pro:
            return self._parse_pro_format(file_path)
        return self._parse_consumer_format(file_path)

    def _check_if_pro(self, file_path: Path) -> bool:
        with open(file_path, mode="r", encoding="utf-8-sig") as f:
            for _ in range(5):
                line = f.readline().lower()
                if "trade id" in line and "product" in line and "side" in line:
                    return True
        return False

    def _parse_consumer_format(self, file_path: Path) -> List[NormalizedTransaction]:
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

                # Seek header row past any metadata preamble
                if header is None:
                    lower_row = [c.lower() for c in cleaned_row]
                    if "timestamp" in lower_row and "transaction type" in lower_row:
                        header = cleaned_row
                        col_map = {c.lower(): idx for idx, c in enumerate(cleaned_row)}
                        continue
                    else:
                        continue

                # Parse transaction row
                tx = self._parse_consumer_row(cleaned_row, col_map, file_path, line_num)
                if tx:
                    transactions.append(tx)

        return transactions

    def _parse_consumer_row(
        self, row: List[str], col_map: Dict[str, int], file_path: Path, line_num: int
    ) -> Optional[NormalizedTransaction]:
        def get_val(key: str, exclude: Optional[str] = None) -> str:
            # Check exact match first
            for k, idx in col_map.items():
                if k == key and idx < len(row):
                    return row[idx]
            # Check prefix match
            for k, idx in col_map.items():
                if k.startswith(key) and idx < len(row):
                    if exclude and exclude in k:
                        continue
                    return row[idx]
            # Check substring match
            for k, idx in col_map.items():
                if key in k and idx < len(row):
                    if exclude and exclude in k:
                        continue
                    return row[idx]
            return ""

        date_str = get_val("timestamp")
        timestamp = self.parse_timestamp(date_str)
        if not timestamp:
            return None

        tx_type_raw = get_val("transaction type")
        asset = self.normalize_currency(get_val("asset"))
        qty = self.parse_decimal(get_val("quantity transacted") or get_val("quantity"))
        spot_curr = self.normalize_currency(get_val("spot price currency") or "USD")
        subtotal = self.parse_decimal(get_val("subtotal"))
        total = self.parse_decimal(get_val("total", exclude="subtotal"))
        fees = self.parse_decimal(get_val("fees and/or spread") or get_val("fee", exclude="total")) or Decimal("0")
        notes = get_val("notes")

        tx_type_lower = tx_type_raw.lower()
        received_amount: Optional[Decimal] = None
        received_curr: Optional[str] = None
        sent_amount: Optional[Decimal] = None
        sent_curr: Optional[str] = None
        fee_amount: Optional[Decimal] = fees if fees and fees > 0 else None
        fee_curr: Optional[str] = spot_curr if fee_amount else None
        tx_type = TransactionType.OTHER

        if "buy" in tx_type_lower:
            tx_type = TransactionType.BUY
            received_amount = qty
            received_curr = asset
            sent_amount = subtotal or (total - fees if total and fees else total)
            sent_curr = spot_curr
        elif "sell" in tx_type_lower:
            tx_type = TransactionType.SELL
            sent_amount = qty
            sent_curr = asset
            received_amount = subtotal or (total + fees if total and fees else total)
            received_curr = spot_curr
        elif "send" in tx_type_lower or "withdrawal" in tx_type_lower:
            tx_type = TransactionType.WITHDRAWAL
            sent_amount = qty
            sent_curr = asset
        elif "receive" in tx_type_lower or "deposit" in tx_type_lower:
            tx_type = TransactionType.DEPOSIT
            received_amount = qty
            received_curr = asset
        elif any(k in tx_type_lower for k in ("income", "reward", "earn", "staking", "interest")):
            tx_type = TransactionType.INCOME
            received_amount = qty
            received_curr = asset
        elif "convert" in tx_type_lower:
            tx_type = TransactionType.TRADE
            # Note description often has converted X to Y
            received_amount = qty
            received_curr = asset

        raw_dict = {f"col_{i}": val for i, val in enumerate(row)}
        for k, v in col_map.items():
            if v < len(row):
                raw_dict[k] = row[v]

        return NormalizedTransaction(
            source_id=f"CB-{line_num}",
            source_file=file_path.name,
            source_line=line_num,
            exchange=self.EXCHANGE_NAME,
            timestamp=timestamp,
            tx_type=tx_type,
            received_amount=received_amount,
            received_currency=received_curr,
            sent_amount=sent_amount,
            sent_currency=sent_curr,
            fee_amount=fee_amount,
            fee_currency=fee_curr,
            order_id=None,
            comment=notes,
            raw_data=raw_dict,
        )

    def _parse_pro_format(self, file_path: Path) -> List[NormalizedTransaction]:
        transactions: List[NormalizedTransaction] = []
        with open(file_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            line_num = 1
            for row in reader:
                line_num += 1
                cleaned_row = {self.clean_string(k).lower(): self.clean_string(v) for k, v in row.items()}
                
                date_str = cleaned_row.get("created at") or cleaned_row.get("time") or cleaned_row.get("timestamp")
                timestamp = self.parse_timestamp(date_str)
                if not timestamp:
                    continue

                trade_id = cleaned_row.get("trade id") or cleaned_row.get("order id")
                side = (cleaned_row.get("side") or "").lower()
                product = cleaned_row.get("product") or ""  # e.g. ETH-USD
                size = self.parse_decimal(cleaned_row.get("size") or cleaned_row.get("amount"))
                size_unit = self.normalize_currency(cleaned_row.get("size unit"))
                price = self.parse_decimal(cleaned_row.get("price"))
                fee = self.parse_decimal(cleaned_row.get("fee"))
                total = self.parse_decimal(cleaned_row.get("total"))
                quote_unit = self.normalize_currency(cleaned_row.get("price/fee/total unit"))

                # Fallback parse base/quote from product if units are missing
                if "-" in product:
                    base_prod, quote_prod = product.split("-", 1)
                    if not size_unit:
                        size_unit = self.normalize_currency(base_prod)
                    if not quote_unit:
                        quote_unit = self.normalize_currency(quote_prod)

                cost = (size * price) if (size and price) else total

                if side == "buy":
                    tx_type = TransactionType.BUY
                    received_amount = size
                    received_curr = size_unit
                    sent_amount = cost
                    sent_curr = quote_unit
                elif side == "sell":
                    tx_type = TransactionType.SELL
                    received_amount = cost
                    received_curr = quote_unit
                    sent_amount = size
                    sent_curr = size_unit
                else:
                    tx_type = TransactionType.TRADE
                    received_amount = size
                    received_curr = size_unit
                    sent_amount = cost
                    sent_curr = quote_unit

                transactions.append(
                    NormalizedTransaction(
                        source_id=f"CBP-{line_num}",
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
                        fee_currency=quote_unit if fee and fee > 0 else None,
                        order_id=trade_id if trade_id else None,
                        comment=f"Coinbase Pro {product} {side.upper()}",
                        raw_data=cleaned_row,
                    )
                )

        return transactions

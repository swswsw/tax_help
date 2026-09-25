"""Parser for Bittrex Order History and Deposits/Withdrawals CSV reports."""

import csv
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

from tax_comparator.models import NormalizedTransaction, TransactionType
from tax_comparator.parsers.base import BaseParser


class BittrexParser(BaseParser):
    """Parses Bittrex Orders CSV and Transfer History CSV reports."""

    EXCHANGE_NAME = "Bittrex"

    @classmethod
    def can_parse(cls, file_path: Path) -> bool:
        try:
            with open(file_path, mode="r", encoding="utf-8-sig") as f:
                first_line = f.readline().lower()
                # Bittrex Orders
                if ("uuid" in first_line or "orderuuid" in first_line) and "exchange" in first_line:
                    return True
                # Bittrex Funding
                if "paymentuuid" in first_line or ("currency" in first_line and "txcost" in first_line):
                    return True
        except Exception:
            return False
        return False

    def parse_file(self, file_path: Path) -> List[NormalizedTransaction]:
        transactions: List[NormalizedTransaction] = []
        with open(file_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            line_num = 1
            for row in reader:
                line_num += 1
                cleaned_row = {self.clean_string(k).lower(): self.clean_string(v) for k, v in row.items()}
                
                # Check whether row is an Order or Transfer
                if "exchange" in cleaned_row or "ordertype" in cleaned_row or "quantity" in cleaned_row:
                    tx = self._parse_order_row(cleaned_row, file_path, line_num)
                else:
                    tx = self._parse_transfer_row(cleaned_row, file_path, line_num)

                if tx:
                    transactions.append(tx)

        return transactions

    def _parse_order_row(self, row: Dict[str, str], file_path: Path, line_num: int) -> Optional[NormalizedTransaction]:
        date_str = row.get("closed") or row.get("timestamp") or row.get("opened")
        timestamp = self.parse_timestamp(date_str)
        if not timestamp:
            return None

        uuid_val = row.get("uuid") or row.get("orderuuid")
        market = row.get("exchange") or ""  # e.g. USD-BTC or BTC-ETH
        order_type_raw = (row.get("ordertype") or row.get("type") or "").upper()
        quantity = self.parse_decimal(row.get("quantity"))
        price = self.parse_decimal(row.get("price"))
        commission = self.parse_decimal(row.get("commission") or row.get("commissionpaid"))

        # In Bittrex: Exchange is "QUOTE-BASE" (e.g. USD-BTC -> quote: USD, base: BTC)
        quote_curr = None
        base_curr = None
        if "-" in market:
            parts = market.split("-", 1)
            quote_curr = self.normalize_currency(parts[0])
            base_curr = self.normalize_currency(parts[1])
        elif "/" in market:
            parts = market.split("/", 1)
            base_curr = self.normalize_currency(parts[0])
            quote_curr = self.normalize_currency(parts[1])

        # If order was partially filled or remaining exists
        qty_rem = self.parse_decimal(row.get("quantityremaining"))
        if qty_rem and quantity and qty_rem > 0:
            quantity = quantity - qty_rem

        if not quantity or quantity <= 0:
            return None

        received_amount: Optional[Decimal] = None
        received_curr: Optional[str] = None
        sent_amount: Optional[Decimal] = None
        sent_curr: Optional[str] = None
        fee_amount: Optional[Decimal] = commission if commission and commission > 0 else None
        fee_curr: Optional[str] = quote_curr if fee_amount else None
        tx_type = TransactionType.OTHER

        if "BUY" in order_type_raw:
            tx_type = TransactionType.BUY
            received_amount = quantity
            received_curr = base_curr
            sent_amount = price
            sent_curr = quote_curr
        elif "SELL" in order_type_raw:
            tx_type = TransactionType.SELL
            received_amount = price
            received_curr = quote_curr
            sent_amount = quantity
            sent_curr = base_curr

        return NormalizedTransaction(
            source_id=f"BIT-{line_num}",
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
            order_id=uuid_val,
            comment=f"Bittrex {market} {order_type_raw}",
            raw_data=row,
        )

    def _parse_transfer_row(self, row: Dict[str, str], file_path: Path, line_num: int) -> Optional[NormalizedTransaction]:
        date_str = row.get("completed") or row.get("opened") or row.get("timestamp") or row.get("date")
        timestamp = self.parse_timestamp(date_str)
        if not timestamp:
            return None

        currency = self.normalize_currency(row.get("currency") or row.get("asset"))
        amount = self.parse_decimal(row.get("amount") or row.get("quantity"))
        fee = self.parse_decimal(row.get("txcost") or row.get("fee"))
        tx_id = row.get("txid") or row.get("paymentuuid")
        tx_type_raw = (row.get("type") or "").lower()

        # Deduce deposit vs withdrawal
        if "deposit" in tx_type_raw or "receive" in tx_type_raw:
            tx_type = TransactionType.DEPOSIT
            received_amount = amount
            received_curr = currency
            sent_amount = None
            sent_curr = None
        else:
            tx_type = TransactionType.WITHDRAWAL
            sent_amount = amount
            sent_curr = currency
            received_amount = None
            received_curr = None

        return NormalizedTransaction(
            source_id=f"BIT-{line_num}",
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
            fee_currency=currency if fee and fee > 0 else None,
            order_id=tx_id,
            comment=f"Bittrex {tx_type.value} {currency}",
            raw_data=row,
        )

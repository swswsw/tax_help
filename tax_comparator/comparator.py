"""Core reconciliation and comparison engine between CoinTracking and exchange records."""

from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
import math
from typing import Dict, List, Optional, Set, Tuple

from tax_comparator.models import (
    ComparisonReport,
    Discrepancy,
    DiscrepancyType,
    MatchedPair,
    NormalizedTransaction,
    TransactionType,
)


class TaxComparator:
    """Compares normalized CoinTracking transactions against exchange records."""

    def __init__(
        self,
        time_tolerance_seconds: int = 120,
        amount_tolerance_percent: float = 0.05,
        detect_timezone_offsets: bool = True,
    ):
        self.time_tolerance_seconds = time_tolerance_seconds
        self.amount_tolerance_percent = amount_tolerance_percent
        self.detect_timezone_offsets = detect_timezone_offsets

    def compare(
        self,
        cointracking_txs: List[NormalizedTransaction],
        exchange_txs: List[NormalizedTransaction],
        exchange_name: str,
        ct_file_name: str,
        ex_file_name: str,
    ) -> ComparisonReport:
        report = ComparisonReport(
            exchange_name=exchange_name,
            cointracking_file=ct_file_name,
            exchange_file=ex_file_name,
            total_cointracking_records=len(cointracking_txs),
            total_exchange_records=len(exchange_txs),
        )

        # 1. Detect internal duplicates in both datasets
        report.cointracking_duplicates = self._find_internal_duplicates(cointracking_txs)
        report.exchange_duplicates = self._find_internal_duplicates(exchange_txs)

        for dups in report.cointracking_duplicates:
            first = dups[0]
            report.discrepancies.append(
                Discrepancy(
                    discrepancy_type=DiscrepancyType.INTERNAL_DUPLICATE_COINTRACKING,
                    severity="HIGH",
                    message=f"CoinTracking contains {len(dups)} duplicate entries for {first.summary_str()} (Lines: {', '.join(str(d.source_line) for d in dups)})",
                    ct_tx=first,
                    details={"lines": [d.source_line for d in dups]},
                )
            )

        for dups in report.exchange_duplicates:
            first = dups[0]
            report.discrepancies.append(
                Discrepancy(
                    discrepancy_type=DiscrepancyType.INTERNAL_DUPLICATE_EXCHANGE,
                    severity="MEDIUM",
                    message=f"Exchange report contains {len(dups)} duplicate entries for {first.summary_str()} (Lines: {', '.join(str(d.source_line) for d in dups)})",
                    exchange_tx=first,
                    details={"lines": [d.source_line for d in dups]},
                )
            )

        # 2. Match CoinTracking and Exchange transactions
        matched_pairs, unmatched_ct, unmatched_ex = self._match_transactions(
            cointracking_txs, exchange_txs
        )
        report.matched_pairs = matched_pairs

        # Filter out excess duplicate copies if another copy of the same transaction was matched
        matched_ct_lines = {pair.ct_tx.source_line for pair in matched_pairs}
        genuine_unmatched_ct = []
        for tx in unmatched_ct:
            is_excess_dup = False
            for group in report.cointracking_duplicates:
                group_lines = {d.source_line for d in group}
                if tx.source_line in group_lines and any(l in matched_ct_lines for l in group_lines):
                    is_excess_dup = True
                    break
            if not is_excess_dup:
                genuine_unmatched_ct.append(tx)

        matched_ex_lines = {pair.exchange_tx.source_line for pair in matched_pairs}
        genuine_unmatched_ex = []
        for tx in unmatched_ex:
            is_excess_dup = False
            for group in report.exchange_duplicates:
                group_lines = {d.source_line for d in group}
                if tx.source_line in group_lines and any(l in matched_ex_lines for l in group_lines):
                    is_excess_dup = True
                    break
            if not is_excess_dup:
                genuine_unmatched_ex.append(tx)

        report.missing_in_exchange = genuine_unmatched_ct
        report.missing_in_cointracking = genuine_unmatched_ex

        # 3. Add discrepancies for missing transactions
        for tx in report.missing_in_cointracking:
            report.discrepancies.append(
                Discrepancy(
                    discrepancy_type=DiscrepancyType.MISSING_IN_COINTRACKING,
                    severity="HIGH",
                    message=f"Missing in CoinTracking: {tx.summary_str()} on {exchange_name} (Line {tx.source_line})",
                    exchange_tx=tx,
                    details={"exchange_line": tx.source_line},
                )
            )

        for tx in report.missing_in_exchange:
            report.discrepancies.append(
                Discrepancy(
                    discrepancy_type=DiscrepancyType.MISSING_IN_EXCHANGE,
                    severity="HIGH",
                    message=f"Missing in {exchange_name} export: CoinTracking entry {tx.summary_str()} (Line {tx.source_line})",
                    ct_tx=tx,
                    details={"cointracking_line": tx.source_line},
                )
            )

        # 4. Collect discrepancies from matched pairs
        for pair in report.matched_pairs:
            for disc in pair.discrepancies:
                report.discrepancies.append(disc)

        return report

    def _find_internal_duplicates(
        self, txs: List[NormalizedTransaction]
    ) -> List[List[NormalizedTransaction]]:
        """Groups transactions that are duplicates of each other."""
        duplicate_groups: List[List[NormalizedTransaction]] = []
        
        # Group by order_id if available
        id_groups: Dict[str, List[NormalizedTransaction]] = defaultdict(list)
        unidentified_txs: List[NormalizedTransaction] = []

        for tx in txs:
            if tx.order_id and len(tx.order_id.strip()) > 2:
                id_groups[tx.order_id.strip()].append(tx)
            else:
                unidentified_txs.append(tx)

        for order_id, group in id_groups.items():
            if len(group) > 1:
                duplicate_groups.append(group)

        # Group remaining by timestamp + amounts + currencies
        fingerprint_groups: Dict[Tuple, List[NormalizedTransaction]] = defaultdict(list)
        for tx in unidentified_txs:
            fp = (
                tx.timestamp,
                tx.tx_type,
                tx.received_amount,
                tx.received_currency,
                tx.sent_amount,
                tx.sent_currency,
            )
            fingerprint_groups[fp].append(tx)

        for fp, group in fingerprint_groups.items():
            if len(group) > 1:
                duplicate_groups.append(group)

        return duplicate_groups

    def _match_transactions(
        self, ct_txs: List[NormalizedTransaction], ex_txs: List[NormalizedTransaction]
    ) -> Tuple[List[MatchedPair], List[NormalizedTransaction], List[NormalizedTransaction]]:
        matched_pairs: List[MatchedPair] = []
        unmatched_ct: Set[int] = set(range(len(ct_txs)))
        unmatched_ex: Set[int] = set(range(len(ex_txs)))

        # Tier 1: Match by exact order ID / tx ID if both have it
        for ct_idx in list(unmatched_ct):
            ct = ct_txs[ct_idx]
            if not ct.order_id:
                continue
            for ex_idx in list(unmatched_ex):
                ex = ex_txs[ex_idx]
                if ex.order_id and ex.order_id.strip().lower() == ct.order_id.strip().lower():
                    time_diff = abs((ct.timestamp - ex.timestamp).total_seconds())
                    pair = MatchedPair(
                        ct_tx=ct,
                        exchange_tx=ex,
                        match_method="EXACT_ID",
                        time_diff_seconds=time_diff,
                    )
                    self._check_pair_discrepancies(pair)
                    matched_pairs.append(pair)
                    unmatched_ct.remove(ct_idx)
                    unmatched_ex.remove(ex_idx)
                    break

        # Tier 2: Fuzzy match by financial amounts and timestamp
        for ct_idx in list(unmatched_ct):
            ct = ct_txs[ct_idx]
            best_match_idx: Optional[int] = None
            best_time_diff = float("inf")
            is_tz_offset = False

            for ex_idx in unmatched_ex:
                ex = ex_txs[ex_idx]

                # Check currency compatibility
                if not self._currencies_compatible(ct, ex):
                    continue

                # Check amount compatibility
                if not self._amounts_compatible(ct, ex):
                    continue

                # Check time difference
                raw_time_diff = (ct.timestamp - ex.timestamp).total_seconds()
                abs_time_diff = abs(raw_time_diff)

                # Direct time tolerance
                if abs_time_diff <= self.time_tolerance_seconds:
                    if abs_time_diff < best_time_diff:
                        best_match_idx = ex_idx
                        best_time_diff = abs_time_diff
                        is_tz_offset = False
                elif self.detect_timezone_offsets:
                    # Check for systematic integer hour offset (e.g. UTC vs local time)
                    remainder = abs(raw_time_diff % 3600)
                    if remainder <= self.time_tolerance_seconds or remainder >= (3600 - self.time_tolerance_seconds):
                        hours_offset = round(raw_time_diff / 3600.0)
                        if 1 <= abs(hours_offset) <= 14:
                            drift_from_hour = abs(raw_time_diff - (hours_offset * 3600))
                            if drift_from_hour < best_time_diff:
                                best_match_idx = ex_idx
                                best_time_diff = drift_from_hour
                                is_tz_offset = True

            if best_match_idx is not None:
                ex = ex_txs[best_match_idx]
                pair = MatchedPair(
                    ct_tx=ct,
                    exchange_tx=ex,
                    match_method="TIMEZONE_ADJUSTED" if is_tz_offset else "FUZZY_FINANCIAL",
                    time_diff_seconds=abs((ct.timestamp - ex.timestamp).total_seconds()),
                )
                self._check_pair_discrepancies(pair)
                matched_pairs.append(pair)
                unmatched_ct.remove(ct_idx)
                unmatched_ex.remove(best_match_idx)

        unmatched_ct_list = [ct_txs[i] for i in sorted(unmatched_ct)]
        unmatched_ex_list = [ex_txs[i] for i in sorted(unmatched_ex)]
        return matched_pairs, unmatched_ct_list, unmatched_ex_list

    def _currencies_compatible(self, ct: NormalizedTransaction, ex: NormalizedTransaction) -> bool:
        # Match primary assets
        ct_assets = {c for c in (ct.received_currency, ct.sent_currency) if c}
        ex_assets = {c for c in (ex.received_currency, ex.sent_currency) if c}

        if not ct_assets or not ex_assets:
            return False

        # Require at least one non-fiat asset to overlap, or if only fiat, exact match
        overlap = ct_assets.intersection(ex_assets)
        if not overlap:
            return False

        # If both legs exist on both sides, check direction or swap
        if ct.received_currency and ex.received_currency:
            if ct.received_currency == ex.received_currency:
                return True
        if ct.sent_currency and ex.sent_currency:
            if ct.sent_currency == ex.sent_currency:
                return True

        return len(overlap) >= 1

    def _amounts_compatible(self, ct: NormalizedTransaction, ex: NormalizedTransaction) -> bool:
        def check_amounts(a: Optional[Decimal], b: Optional[Decimal]) -> bool:
            if a is None and b is None:
                return True
            if a is None or b is None:
                return True  # Loose matching if one side lacks fiat/crypto leg
            if a == 0 and b == 0:
                return True
            diff = abs(a - b)
            avg = (a + b) / Decimal("2")
            if avg == 0:
                return diff == 0
            pct = (diff / avg) * Decimal("100")
            return pct <= Decimal(str(self.amount_tolerance_percent)) or diff <= Decimal("0.000001")

        # Received amount match
        if ct.received_amount and ex.received_amount and ct.received_currency == ex.received_currency:
            if not check_amounts(ct.received_amount, ex.received_amount):
                return False

        # Sent amount match
        if ct.sent_amount and ex.sent_amount and ct.sent_currency == ex.sent_currency:
            if not check_amounts(ct.sent_amount, ex.sent_amount):
                return False

        return True

    def _check_pair_discrepancies(self, pair: MatchedPair) -> None:
        ct = pair.ct_tx
        ex = pair.exchange_tx

        # 1. Check Timezone offset or Time drift
        raw_diff_seconds = (ct.timestamp - ex.timestamp).total_seconds()
        hours_offset = round(raw_diff_seconds / 3600.0)
        if abs(hours_offset) >= 1 and abs(raw_diff_seconds - (hours_offset * 3600)) <= self.time_tolerance_seconds:
            pair.discrepancies.append(
                Discrepancy(
                    discrepancy_type=DiscrepancyType.TIMEZONE_OFFSET,
                    severity="MEDIUM",
                    message=f"Timezone offset detected: CoinTracking is {hours_offset:+d} hour(s) relative to exchange timestamp ({ct.timestamp.strftime('%H:%M:%S')} vs {ex.timestamp.strftime('%H:%M:%S')})",
                    ct_tx=ct,
                    exchange_tx=ex,
                    details={"offset_hours": hours_offset, "diff_seconds": raw_diff_seconds},
                )
            )
        elif abs(raw_diff_seconds) > 15:
            pair.discrepancies.append(
                Discrepancy(
                    discrepancy_type=DiscrepancyType.TIMESTAMP_MISMATCH,
                    severity="LOW",
                    message=f"Timestamp drift of {int(abs(raw_diff_seconds))}s (CT: {ct.timestamp.strftime('%Y-%m-%d %H:%M:%S')}, EX: {ex.timestamp.strftime('%Y-%m-%d %H:%M:%S')})",
                    ct_tx=ct,
                    exchange_tx=ex,
                    details={"diff_seconds": raw_diff_seconds},
                )
            )

        # 2. Check Amount discrepancies
        if ct.received_amount and ex.received_amount and ct.received_currency == ex.received_currency:
            diff = abs(ct.received_amount - ex.received_amount)
            if diff > Decimal("0.0000001"):
                pct = (diff / ex.received_amount) * Decimal("100") if ex.received_amount else Decimal("0")
                if pct > Decimal(str(self.amount_tolerance_percent)):
                    pair.discrepancies.append(
                        Discrepancy(
                            discrepancy_type=DiscrepancyType.AMOUNT_MISMATCH,
                            severity="HIGH",
                            message=f"Received amount mismatch: CT logged {ct.received_amount} {ct.received_currency}, but exchange shows {ex.received_amount} {ex.received_currency} (Diff: {diff})",
                            ct_tx=ct,
                            exchange_tx=ex,
                            details={"ct_amount": str(ct.received_amount), "ex_amount": str(ex.received_amount), "diff": str(diff)},
                        )
                    )

        if ct.sent_amount and ex.sent_amount and ct.sent_currency == ex.sent_currency:
            diff = abs(ct.sent_amount - ex.sent_amount)
            if diff > Decimal("0.0000001"):
                pct = (diff / ex.sent_amount) * Decimal("100") if ex.sent_amount else Decimal("0")
                if pct > Decimal(str(self.amount_tolerance_percent)):
                    pair.discrepancies.append(
                        Discrepancy(
                            discrepancy_type=DiscrepancyType.AMOUNT_MISMATCH,
                            severity="HIGH",
                            message=f"Sent amount mismatch: CT logged {ct.sent_amount} {ct.sent_currency}, but exchange shows {ex.sent_amount} {ex.sent_currency} (Diff: {diff})",
                            ct_tx=ct,
                            exchange_tx=ex,
                            details={"ct_amount": str(ct.sent_amount), "ex_amount": str(ex.sent_amount), "diff": str(diff)},
                        )
                    )

        # 3. Check Fee discrepancies
        if ex.fee_amount and ex.fee_amount > 0:
            if not ct.fee_amount or ct.fee_amount == 0:
                pair.discrepancies.append(
                    Discrepancy(
                        discrepancy_type=DiscrepancyType.FEE_MISMATCH,
                        severity="MEDIUM",
                        message=f"Missing fee in CoinTracking: Exchange recorded fee of {ex.fee_amount} {ex.fee_currency}, but CT has no fee.",
                        ct_tx=ct,
                        exchange_tx=ex,
                        details={"exchange_fee": str(ex.fee_amount), "fee_currency": ex.fee_currency},
                    )
                )
            elif ct.fee_amount and ct.fee_currency == ex.fee_currency:
                fee_diff = abs(ct.fee_amount - ex.fee_amount)
                if fee_diff > Decimal("0.0000001"):
                    pair.discrepancies.append(
                        Discrepancy(
                            discrepancy_type=DiscrepancyType.FEE_MISMATCH,
                            severity="LOW",
                            message=f"Fee amount discrepancy: CT logged {ct.fee_amount} {ct.fee_currency}, but exchange logged {ex.fee_amount} {ex.fee_currency}",
                            ct_tx=ct,
                            exchange_tx=ex,
                            details={"ct_fee": str(ct.fee_amount), "ex_fee": str(ex.fee_amount)},
                        )
                    )
            elif ct.fee_amount and ct.fee_currency != ex.fee_currency:
                pair.discrepancies.append(
                    Discrepancy(
                        discrepancy_type=DiscrepancyType.FEE_MISMATCH,
                        severity="MEDIUM",
                        message=f"Fee currency mismatch: CT logged fee in {ct.fee_currency}, but exchange logged in {ex.fee_currency}",
                        ct_tx=ct,
                        exchange_tx=ex,
                    )
                )

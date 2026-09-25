# Tax Comparator Architecture & Extensibility Guide

This document describes the software architecture, core data models, matching algorithms, and extensibility patterns of the **Tax Comparator** utility.

---

## 1. High-Level Architecture

The system is organized into modular layers separating ingestion, normalization, matching, and reporting:

```
┌─────────────────────────────────┐       ┌─────────────────────────────────┐
│     CoinTracking CSV Export     │       │     Exchange CSV Export         │
│  (Trade Table, repeated Cur.)   │       │  (Coinbase, Gemini, Bittrex)    │
└────────────────┬────────────────┘       └────────────────┬────────────────┘
                 │                                         │
                 ▼                                         ▼
   ┌───────────────────────────┐             ┌───────────────────────────┐
   │    CoinTrackingParser     │             │    Exchange Specific      │
   │  (Filter by exchange)     │             │         Parser            │
   └─────────────┬─────────────┘             └─────────────┬─────────────┘
                 │                                         │
                 └──────────────┐           ┌──────────────┘
                                ▼           ▼
                        ┌───────────────────────────────┐
                        │   NormalizedTransaction (xN)  │
                        │   - UTC Datetime              │
                        │   - Standard Tickers          │
                        │   - Decimal Quantities        │
                        └───────────────┬───────────────┘
                                        │
                                        ▼
                        ┌───────────────────────────────┐
                        │        TaxComparator          │
                        │ 1. Internal Deduplication     │
                        │ 2. Tier-1: Exact Order ID     │
                        │ 3. Tier-2: Fuzzy Financial    │
                        │ 4. Tier-3: Timezone Offsets   │
                        │ 5. Discrepancy Analysis       │
                        └───────────────┬───────────────┘
                                        │
                                        ▼
                        ┌───────────────────────────────┐
                        │       ComparisonReport        │
                        │ - Exact matches               │
                        │ - Matched w/ discrepancies    │
                        │ - Missing records             │
                        │ - Internal duplicates         │
                        └───────────────┬───────────────┘
                                        │
                 ┌──────────────────────┼──────────────────────┐
                 ▼                      ▼                      ▼
         ┌───────────────┐      ┌───────────────┐      ┌───────────────┐
         │  Rich Console │      │  JSON Export  │      │ Markdown Doc  │
         │     Table     │      │  (Automation) │      │   (Audit)     │
         └───────────────┘      └───────────────┘      └───────────────┘
```

---

## 2. Core Data Models (`tax_comparator/models.py`)

### 2.1 `NormalizedTransaction`
Every transaction is parsed into a platform-agnostic, canonical representation:

```python
@dataclass
class NormalizedTransaction:
  source_id: str  # Generated unique source row tag (e.g., CB-10)
  source_file: str  # Filename
  source_line: int  # 1-indexed line number in original CSV
  exchange: str  # Canonical exchange name
  timestamp: datetime  # Timezone-aware UTC datetime
  tx_type: TransactionType  # BUY, SELL, TRADE, DEPOSIT, WITHDRAWAL, etc.
  received_amount: Optional[Decimal]  # Magnitude received
  received_currency: Optional[str]  # Standard uppercase ticker
  sent_amount: Optional[Decimal]  # Magnitude disposed
  sent_currency: Optional[str]  # Standard uppercase ticker
  fee_amount: Optional[Decimal]  # Fee paid
  fee_currency: Optional[str]  # Currency of fee
  order_id: Optional[str]  # Exchange Order/Trade ID (if available)
  comment: Optional[str]  # Trade notes or descriptions
  raw_data: Dict[str, Any]  # Dictionary of raw row data for inspection
```

### 2.2 `ComparisonReport`
Aggregates reconciliation metrics, duplicate groups, matched pairs, missing items, and granular discrepancies.

---

## 3. Reconciliation & Matching Algorithm

The matching process in `tax_comparator/comparator.py` executes in five distinct phases:

### Phase 1: Internal Deduplication
Before comparing datasets, both the CoinTracking list and Exchange list are checked internally for duplicate records:
- **Order ID Match**: Multiple records sharing identical non-empty `order_id`s.
- **Fingerprint Match**: For records without order IDs, matching on tuple `(timestamp, tx_type, received_amount, received_currency, sent_amount, sent_currency)`.
- If an internal duplicate in CoinTracking matches an exchange record, only the primary copy is linked; the excess copies are flagged as internal duplicates rather than falsely reported as missing exchange trades.

### Phase 2: Tier-1 Exact ID Matching
If both transactions contain non-empty order IDs:
$$\text{ct\_tx.order\_id.lower()} == \text{exchange\_tx.order\_id.lower()}$$
These records are paired immediately with 100% confidence.

### Phase 3: Tier-2 Fuzzy Financial Matching
For remaining unmatched transactions:
1. **Asset Compatibility**: Confirms that non-fiat asset tickers overlap, and trade direction matches.
2. **Amount Compatibility**: Checks both received and sent amounts:
   $$\frac{|A - B|}{\frac{A + B}{2}} \times 100 \le \text{amount\_tolerance\_percent}$$
   or $|A - B| \le 10^{-6}$ (to handle floating point rounding differences).
3. **Time Window**: Evaluates time difference:
   $$|\text{timestamp}_{\text{ct}} - \text{timestamp}_{\text{exchange}}| \le \text{time\_tolerance\_seconds}$$

### Phase 4: Tier-3 Timezone Offset Detection
If transactions match financially and the sub-hour drift is within tolerance, but the timestamps differ by approximately an integer number of hours:
$$|\Delta t \pmod{3600}| \le \text{tolerance} \quad \text{or} \quad 3600 - |\Delta t \pmod{3600}| \le \text{tolerance}$$
$$\text{hours\_offset} = \text{round}\left(\frac{\Delta t}{3600}\right) \in [-14, 14]$$
The pair is matched, and a `TIMEZONE_OFFSET` discrepancy is recorded, informing the user that their CoinTracking export is in local time rather than UTC.

### Phase 5: Discrepancy & Inconsistency Analysis
For each matched pair, the engine checks for:
- **Amount Mismatch**: Received or sent quantities differing beyond tolerance (identifying net proceeds vs gross proceeds).
- **Fee Omission**: Fee recorded on the exchange, but recorded as $0$ or missing in CoinTracking.
- **Fee Amount Discrepancy**: Difference in fee amounts.
- **Fee Currency Mismatch**: Fee logged in cryptocurrency on one platform but in fiat on another.
- **Timestamp Drift**: Deviations greater than 15 seconds.

---

## 4. How to Add a New Exchange Parser

To add support for a new exchange (e.g., **Kraken** or **Binance**):

### Step 1: Create the Parser Class
Create a new file in `tax_comparator/parsers/` subclassing `BaseParser`:

```python
# tax_comparator/parsers/kraken.py
import csv
from decimal import Decimal
from pathlib import Path
from typing import List, Optional

from tax_comparator.models import NormalizedTransaction, TransactionType
from tax_comparator.parsers.base import BaseParser


class KrakenParser(BaseParser):
  EXCHANGE_NAME = "Kraken"

  @classmethod
  def can_parse(cls, file_path: Path) -> bool:
    """Check if header matches Kraken export layout."""
    try:
      with open(file_path, "r", encoding="utf-8-sig") as f:
        first_line = f.readline().lower()
        return "txid" in first_line and "ordertxid" in first_line
    except Exception:
      return False

  def parse_file(self, file_path: Path) -> List[NormalizedTransaction]:
    transactions = []
    with open(file_path, "r", encoding="utf-8-sig") as f:
      reader = csv.DictReader(f)
      line_num = 1
      for row in reader:
        line_num += 1
        # Extract fields using BaseParser helpers:
        # self.parse_timestamp(...)
        # self.parse_decimal(...)
        # self.normalize_currency(...)
        ...
    return transactions
```

### Step 2: Register in `tax_comparator/parsers/__init__.py`
Add the new parser to `PARSER_REGISTRY` and auto-detection sequence:

```python
from tax_comparator.parsers.kraken import KrakenParser

PARSER_REGISTRY["kraken"] = KrakenParser
```

### Step 3: Add Unit Tests
Add sample CSV and tests in `tests/test_parsers.py` to ensure high test coverage.

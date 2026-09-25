# Cryptocurrency Export CSV Format Specifications

This document provides a detailed reference for the CSV export formats used by **CoinTracking** and the cryptocurrency exchanges **Coinbase** (Retail & Pro), **Gemini**, and **Bittrex**. It details column layouts, data types, timestamp conventions, transaction representations, and common edge cases.

---

## 1. CoinTracking CSV Export Format

CoinTracking is a portfolio tracker and tax calculator. Users export their transaction records (from the "Trade Table" / "Enter Coins" view) to back up, audit, or migrate data.

### Standard Trade Table Export Layout

CoinTracking's export format represents trades, deposits, withdrawals, and income within a unified tabular structure where **both legs of a trade** are captured in a single row.

| Column Index | Header Name | Data Type | Description |
| :--- | :--- | :--- | :--- |
| 1 | `Type` | String | Transaction type: `Trade`, `Deposit`, `Withdrawal`, `Income`, `Mining`, `Staking`, `Reward / Bonus`, `Airdrop`, `Spend`, `Lost`, `Gift` |
| 2 | `Buy` | Decimal | Amount of asset received/acquired (empty for withdrawals/expenses) |
| 3 | `Cur.` | String | Currency/ticker symbol for the asset received (e.g., `BTC`, `ETH`, `USD`) |
| 4 | `Sell` | Decimal | Amount of asset disposed/spent (empty for deposits/income) |
| 5 | `Cur.` | String | Currency/ticker symbol for the asset disposed (e.g., `USD`, `ETH`) |
| 6 | `Fee` | Decimal | Trading or transfer fee amount (optional, may be empty or `0`) |
| 7 | `Cur.` | String | Currency ticker for the fee (e.g., `USD`, `BTC`, `BNB`) |
| 8 | `Exchange` | String | Exchange or wallet name (e.g., `Coinbase`, `Gemini`, `Bittrex`) |
| 9 | `Group` | String | User-defined group tag (e.g., `Trading`, `HODL`, `Taxes 2021`) |
| 10 | `Comment` | String | User notes or trade descriptions |
| 11 | `Date` | Timestamp | Transaction timestamp (e.g., `YYYY-MM-DD HH:MM:SS` or `DD.MM.YYYY HH:MM:SS`) |
| 12 | `Tx-ID` | String | *(Optional)* Exchange Trade ID or blockchain transaction hash |

> **Note on Duplicate Headers**: Notice that `Cur.` appears three times (Buy Currency, Sell Currency, Fee Currency). Parsers must identify currency columns by position relative to their corresponding quantity columns rather than relying strictly on unique column names.

### Transaction Representation Conventions:
- **Trade (Swap / Spot Fill)**: Both `Buy` and `Sell` are populated. For example, buying 1.5 ETH with $4,500 USD: `Buy=1.5`, `Cur.=ETH`, `Sell=4500`, `Cur.=USD`.
- **Deposit**: `Buy` and its `Cur.` are populated; `Sell` and its `Cur.` are empty.
- **Withdrawal**: `Sell` and its `Cur.` are populated; `Buy` and its `Cur.` are empty.
- **Fee**: Can be denominated in the buy asset, the sell asset, or a third asset (e.g. BNB or exchange token).

### Sample CoinTracking CSV:
```csv
"Type","Buy","Cur.","Sell","Cur.","Fee","Cur.","Exchange","Group","Comment","Date","Tx-ID"
"Trade","1.50000000","ETH","4500.00","USD","15.00","USD","Coinbase","","Bought ETH on Coinbase","2021-05-10 14:23:05","CB-TR-1001"
"Trade","0.10000000","BTC","3200.00","USD","11.20","USD","Gemini","","Limit Buy BTC","2021-06-15 10:15:30","GEM-987654"
"Trade","2.50000000","LTC","0.01500000","BTC","0.00003750","BTC","Bittrex","","LTC/BTC limit buy","2021-07-20 18:45:12","bit-order-5544"
"Deposit","5000.00","USD","","","0.00","USD","Coinbase","","ACH Deposit","2021-05-01 09:00:00",""
"Withdrawal","","","0.50000000","ETH","0.00500000","ETH","Coinbase","","Withdraw to Ledger","2021-06-01 12:00:00","0xabc123456789def"
```

---

## 2. Coinbase Export CSV Formats

Coinbase provides two primary report exports: **Coinbase Consumer (Retail)** and **Coinbase Pro / Advanced Trade**.

### 2.1 Coinbase Consumer (Retail) Transaction Report

#### Preamble Structure
Coinbase Consumer exports begin with metadata preamble rows (typically 4–8 rows) before the actual column header appears:
```text
Coinbase Reports
Transactions
User,Jane Doe
Email,jane@example.com
Timestamp,Transaction Type,Asset,Quantity Transacted,Spot Price Currency,Spot Price at Transaction,Subtotal,Total (inclusive of fees and/or spread),Fees and/or Spread,Notes
```

#### Column Schema
| Header | Type | Description |
| :--- | :--- | :--- |
| `Timestamp` | ISO Timestamp | Execution timestamp in UTC (e.g., `2021-05-10T14:23:05Z` or `2021-05-10 14:23:05 UTC`) |
| `Transaction Type` | String | `Buy`, `Sell`, `Send` (Withdrawal), `Receive` (Deposit), `Convert`, `Rewards Income`, `Coinbase Earn` |
| `Asset` | String | Asset ticker symbol (e.g., `BTC`, `ETH`, `USDC`) |
| `Quantity Transacted` | Decimal | Amount of crypto transacted |
| `Spot Price Currency` | String | Fiat or base pricing currency (typically `USD`) |
| `Spot Price at Transaction` | Decimal | Unit price in spot currency |
| `Subtotal` | Decimal | Net fiat value before fees |
| `Total (inclusive of fees and/or spread)` | Decimal | Total fiat charged/credited |
| `Fees and/or Spread` | Decimal | Transaction fee paid in fiat |
| `Notes` | String | Human readable description (e.g., `Bought 1.5000 ETH for $4515.00 USD`) |

#### Sample Coinbase Retail CSV:
```csv
Coinbase Transaction Report
Generated at 2021-12-31 23:59:59 UTC
User: Satoshi Nakamoto

Timestamp,Transaction Type,Asset,Quantity Transacted,Spot Price Currency,Spot Price at Transaction,Subtotal,Total (inclusive of fees and/or spread),Fees and/or Spread,Notes
2021-05-10T14:23:05Z,Buy,ETH,1.5,USD,3000.00,4500.00,4515.00,15.00,Bought 1.5000 ETH for $4515.00 USD
2021-05-01T09:00:00Z,Receive,USD,5000.00,USD,1.00,5000.00,5000.00,0.00,Bank deposit received
2021-06-01T12:00:00Z,Send,ETH,0.5,USD,2800.00,1400.00,1414.00,14.00,Sent 0.5 ETH to external address
2021-08-14T19:30:00Z,Sell,BTC,0.05,USD,45000.00,2250.00,2235.00,15.00,Sold 0.0500 BTC for $2235.00 USD
```

---

### 2.2 Coinbase Pro / Advanced Trade Fills

Coinbase Pro exports each individual order fill with clean headers and no preamble.

#### Column Schema
```text
portfolio,trade id,product,side,created at,size,size unit,price,fee,total,price/fee/total unit
```

| Header | Type | Description |
| :--- | :--- | :--- |
| `portfolio` | String | Portfolio name (e.g., `default`) |
| `trade id` | String / Int | Unique execution identifier (e.g., `12345678`) |
| `product` | String | Market pair (e.g., `ETH-USD`, `BTC-USD`) |
| `side` | String | `BUY` or `SELL` |
| `created at` | ISO Timestamp | Fill timestamp (e.g., `2021-05-10T14:23:05.123Z`) |
| `size` | Decimal | Amount of the base asset |
| `size unit` | String | Base asset symbol (e.g., `ETH`) |
| `price` | Decimal | Execution price per unit |
| `fee` | Decimal | Exchange fee charged |
| `total` | Decimal | Total fiat cost/proceeds |
| `price/fee/total unit`| String | Quote asset symbol (e.g., `USD`) |

#### Sample Coinbase Pro CSV:
```csv
portfolio,trade id,product,side,created at,size,size unit,price,fee,total,price/fee/total unit
default,CB-TR-1001,ETH-USD,BUY,2021-05-10T14:23:05.000Z,1.5,ETH,3000.00,15.00,-4515.00,USD
default,CB-TR-1002,BTC-USD,SELL,2021-08-14T19:30:00.000Z,0.05,BTC,45000.00,6.75,2243.25,USD
```

---

## 3. Gemini Export CSV Formats

Gemini provides two distinct transaction report exports: **ActiveTrader Order History** (trade executions) and **Account Transaction / Transfer History** (deposits, withdrawals, fees).

### 3.1 Gemini ActiveTrader / Order History

#### Column Schema
```text
Date,Time (UTC),Type,Symbol,Specification,Liquidity Indicator,Trading Fee Rate (bps),USD Amount,Trading Fee (USD),Net Proceeds (USD),BTC Amount
```
*(Note: The crypto amount column header dynamically corresponds to the traded symbol, e.g. `BTC Amount`, `ETH Amount`, or generic `Amount`).*

| Header | Type | Description |
| :--- | :--- | :--- |
| `Date` | Date String | Calendar date (`YYYY-MM-DD`) |
| `Time (UTC)` | Time String | Time in UTC (`HH:MM:SS` or `HH:MM:SS.sss`) |
| `Type` | String | Order side: `Buy`, `Sell`, `Block Trade`, `Auction` |
| `Symbol` | String | Market pair ticker (e.g., `BTCUSD`, `ETHUSD`, `ETHBTC`) |
| `Specification` | String | Order specification details |
| `Liquidity Indicator`| String | `Maker` or `Taker` |
| `Trading Fee Rate (bps)`| Decimal | Fee rate in basis points ($10\text{ bps} = 0.10\%$) |
| `USD Amount` | String / Decimal| Gross fiat value (often formatted with currency signs e.g., `$3,200.00`) |
| `Trading Fee (USD)` | String / Decimal| Fee charged in USD (e.g., `$11.20`) |
| `Net Proceeds (USD)`| String / Decimal| Total net proceeds or debit (e.g., `-$3,211.20` or `+$3,188.80`) |
| `<Crypto> Amount` | Decimal | Amount of cryptocurrency executed (e.g. `0.10000000`) |

### 3.2 Gemini Account Transaction / Transfer History

#### Column Schema
```text
Date,Time (UTC),Type,Symbol,Specification,Amount,Fee,USD Amount
```
or generic:
```text
Date,Time (UTC),Type,Symbol,Amount,Price,Fee,Fee Currency
```
- `Type`: `Deposit`, `Withdrawal`, `Credit`, `Administrative`, `Buy`, `Sell`
- `Amount`: Numerical volume transferred or traded

#### Sample Gemini CSV:
```csv
Date,Time (UTC),Type,Symbol,Specification,Liquidity Indicator,Trading Fee Rate (bps),USD Amount,Trading Fee (USD),Net Proceeds (USD),BTC Amount
2021-06-15,10:15:30,Buy,BTCUSD,Limit,Taker,35.00,$3200.00,$11.20,-$3211.20,0.10000000
2021-09-01,16:40:10,Sell,ETHUSD,Limit,Maker,10.00,$7000.00,$7.00,+$6993.00,2.00000000
```

---

## 4. Bittrex Export CSV Formats

Bittrex historically provided order history exports and funding (deposits/withdrawals) exports before its liquidation.

### 4.1 Bittrex Orders / Trade History

Bittrex represents market pairs in the format `QUOTE-BASE` (or `BaseCurrency-MarketCurrency`):
- `USD-BTC`: Quote is `USD`, Base traded is `BTC`.
- `BTC-ETH`: Quote is `BTC`, Base traded is `ETH`.

#### Column Schema
```text
Uuid,Exchange,TimeStamp,OrderType,Limit,Quantity,QuantityRemaining,Commission,Price,PricePerUnit,IsConditional,Condition,ConditionTarget,ImmediateOrCancel,Closed
```

| Header | Type | Description |
| :--- | :--- | :--- |
| `Uuid` | UUID String | Unique order identifier (e.g., `0c1d2e3f-4a5b-6c7d-8e9f-0a1b2c3d4e5f`) |
| `Exchange` | String | Trading pair symbol (e.g., `USD-BTC`, `BTC-LTC`) |
| `TimeStamp` | Timestamp | Order creation timestamp (`MM/DD/YYYY HH:MM:SS AM/PM` or ISO format) |
| `OrderType` | String | `LIMIT_BUY`, `LIMIT_SELL`, `MARKET_BUY`, `MARKET_SELL` |
| `Limit` | Decimal | Specified limit price per unit |
| `Quantity` | Decimal | Executed base asset quantity |
| `QuantityRemaining`| Decimal | Unfilled portion (should be `0.00000000` for completed trades) |
| `Commission` | Decimal | Exchange commission/fee (in quote currency) |
| `Price` | Decimal | Total quote currency value of the trade |
| `PricePerUnit` | Decimal | Effective executed price per unit |
| `Closed` | Timestamp | Timestamp when the order was completed |

### 4.2 Bittrex Deposits & Withdrawals

#### Column Schema
```text
PaymentUuid,Currency,Amount,Address,Opened,Authorized,Pending,Completed,TxCost,TxId
```
- `PaymentUuid`: Unique deposit or withdrawal UUID
- `Currency`: Asset symbol (e.g., `BTC`, `ETH`, `USDT`)
- `Amount`: Transferred quantity
- `TxCost`: Network transaction fee paid
- `Completed`: Confirmation timestamp

#### Sample Bittrex Orders CSV:
```csv
Uuid,Exchange,TimeStamp,OrderType,Limit,Quantity,QuantityRemaining,Commission,Price,PricePerUnit,IsConditional,Condition,ConditionTarget,ImmediateOrCancel,Closed
bit-order-5544,BTC-LTC,7/20/2021 6:45:12 PM,LIMIT_BUY,0.00600000,2.50000000,0.00000000,0.00003750,0.01500000,0.00600000,False,NONE,None,False,7/20/2021 6:45:12 PM
bit-order-7788,USD-BTC,8/05/2021 11:20:00 AM,LIMIT_SELL,40000.00,0.25000000,0.00000000,25.00,10000.00,40000.00,False,NONE,None,False,8/05/2021 11:20:00 AM
```

---

## 5. Normalization & Reconciliation Mapping

To compare CoinTracking data against these three exchanges, all records must be normalized into a unified intermediate data structure:

```python
class NormalizedTransaction:
  timestamp: datetime  # UTC normalized
  tx_type: (
      TransactionType  # BUY, SELL, TRADE, DEPOSIT, WITHDRAWAL, INCOME, OTHER
  )
  received_amount: Decimal  # Positive amount received
  received_currency: str  # Standard uppercase ticker
  sent_amount: Decimal  # Positive amount sent
  sent_currency: str  # Standard uppercase ticker
  fee_amount: Decimal  # Transaction fee paid
  fee_currency: str  # Currency ticker for fee
  order_id: str  # Exchange Trade ID / Tx-ID
  exchange: str  # Source exchange name
  source_file: str  # Originating file path
  source_line: int  # Line number in CSV
  raw_data: dict  # Original parsed row
```

### Mapping Matrix

| Source Platform | Type / Side | Received Leg | Sent Leg | Fee Leg |
| :--- | :--- | :--- | :--- | :--- |
| **CoinTracking** | `Trade` | `Buy` + `Cur.[0]` | `Sell` + `Cur.[1]` | `Fee` + `Cur.[2]` |
| **CoinTracking** | `Deposit` | `Buy` + `Cur.[0]` | None | `Fee` + `Cur.[2]` |
| **CoinTracking** | `Withdrawal` | None | `Sell` + `Cur.[1]` | `Fee` + `Cur.[2]` |
| **Coinbase Retail** | `Buy` | `Quantity Transacted` (`Asset`) | `Subtotal` (`Spot Price Currency`) | `Fees and/or Spread` |
| **Coinbase Retail** | `Sell` | `Subtotal` (`Spot Price Currency`) | `Quantity Transacted` (`Asset`) | `Fees and/or Spread` |
| **Coinbase Retail** | `Send` | None | `Quantity Transacted` (`Asset`) | `Fees and/or Spread` |
| **Coinbase Retail** | `Receive` | `Quantity Transacted` (`Asset`) | None | `Fees and/or Spread` |
| **Coinbase Pro** | `BUY` | `size` (`size unit`) | `price * size` (`price unit`) | `fee` (`fee unit`) |
| **Coinbase Pro** | `SELL` | `price * size` (`price unit`) | `size` (`size unit`) | `fee` (`fee unit`) |
| **Gemini Active** | `Buy` | `<Crypto> Amount` (`Base`) | `USD Amount` (`USD`) | `Trading Fee (USD)` |
| **Gemini Active** | `Sell` | `USD Amount` (`USD`) | `<Crypto> Amount` (`Base`) | `Trading Fee (USD)` |
| **Bittrex Orders**| `LIMIT_BUY` | `Quantity` (`Base`) | `Price` (`Quote`) | `Commission` (`Quote`) |
| **Bittrex Orders**| `LIMIT_SELL`| `Price` (`Quote`) | `Quantity` (`Base`) | `Commission` (`Quote`) |

### Inconsistencies Detected:
1. **Duplicate Records**: Duplicate transactions imported into CoinTracking (e.g. from both API sync and CSV import).
2. **Missing Records**:
   - Exchange transactions never logged in CoinTracking.
   - CoinTracking manual records tagged with the exchange that have no corresponding exchange match.
3. **Discrepancies**:
   - Amount differences (e.g. gross vs net amounts, fee deductions).
   - Fee discrepancies (missing fees in CoinTracking, fee currency mismatches).
   - Timestamp differences & Timezone offsets (e.g., UTC vs local time differences like +4h, +5h, +8h).

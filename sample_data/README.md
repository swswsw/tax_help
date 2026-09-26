# Sample Transaction Datasets

This directory contains real-world and reference CSV exports representing the various format variations supported by the reconciliation engine.

---

## Datasets Overview

| Filename | Platform / Source | Format Type | Description |
| :--- | :--- | :--- | :--- |
| **`cointracking_sample.csv`** | CoinTracking | Trade Table Export | Standard unified layout containing dual-leg trades, duplicate entries, fees, and transfers across Coinbase, Gemini, and Bittrex. |
| **`cointracking_custom_import_sample.csv`** | CoinTracking | Custom Import Template | Alternative CoinTracking template using `Buy Amount`, `Buy Cur.`, `Sell Amount`, `Sell Cur.` headers. |
| **`coinbase_retail_sample.csv`** | Coinbase | Consumer Transaction History | Standard retail report with metadata preamble, subtotal, gross total with spread, fees, and notes. |
| **`coinbase_pro_sample.csv`** | Coinbase Pro | Historical Fills | Legacy GDAX / Coinbase Pro order fills format (`trade id,product,side,created at,size,price,fee,total`). |
| **`coinbase_advanced_fills_sample.csv`** | Coinbase Pro / Advanced | Advanced Fills | Multi-asset order fills with high-precision decimals and fee deductions. |
| **`gemini_sample.csv`** | Gemini | ActiveTrader Orders | High-volume trading export with maker/taker liquidity indicators, fee rates in basis points, and dynamic asset quantity columns. |
| **`gemini_transfers_sample.csv`** | Gemini | Account Transfers | Fiat wire deposits, crypto deposits, and external withdrawals. |
| **`bittrex_sample.csv`** | Bittrex | Closed Orders History | Historical closed orders with `QUOTE-BASE` pair markets (e.g., `USD-BTC`, `BTC-LTC`), commissions, and limit prices. |
| **`bittrex_transfers_sample.csv`** | Bittrex | Deposits & Withdrawals | Historical funding history with `PaymentUuid`, transaction costs (`TxCost`), and blockchain transaction IDs (`TxId`). |

---

## Running Quick Reconciliations with Sample Data

### 1. Coinbase Consumer Reconciliation
```bash
python3 -m tax_comparator.cli \
  -c sample_data/cointracking_sample.csv \
  -e sample_data/coinbase_retail_sample.csv \
  -x coinbase
```

### 2. Gemini ActiveTrader Reconciliation (with automatic timezone offset detection)
```bash
python3 -m tax_comparator.cli \
  -c sample_data/cointracking_sample.csv \
  -e sample_data/gemini_sample.csv \
  -x gemini
```

### 3. Bittrex Closed Orders Reconciliation
```bash
python3 -m tax_comparator.cli \
  -c sample_data/cointracking_sample.csv \
  -e sample_data/bittrex_sample.csv \
  -x bittrex
```

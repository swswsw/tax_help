# Documentation Sources & References

This document records the official documentation, knowledge base resources, API specifications, and open-source references used to determine the exact CSV file formats and data models for **CoinTracking**, **Coinbase**, **Gemini**, and **Bittrex**.

---

## 1. CoinTracking CSV Format Sources

### Official Knowledge Base & Documentation:
- **CoinTracking Custom Exchange / CSV Import Specification**:
  - URL: [https://cointracking.info/import/cointracking_csv/](https://cointracking.info/import/cointracking_csv/)
  - Details: Official specification of CoinTracking's internal CSV columns, date formatting expectations, transaction type tags, and fee column positions.
- **CoinTracking Freshdesk Knowledge Base**:
  - Article: *"CoinTracking Excel / CSV Import Guide"*
  - URL: [https://cointracking.freshdesk.com/en/support/solutions/articles/29000007202-cointracking-excel-csv-import](https://cointracking.freshdesk.com/en/support/solutions/articles/29000007202-cointracking-excel-csv-import)
  - Details: Rules for handling buy/sell pairs in single rows vs single-sided deposits/withdrawals, repeated `Cur.` headers, and trade groups.
- **CoinTracking General Import Instructions**:
  - URL: [https://cointracking.info/import_instructions.php](https://cointracking.info/import_instructions.php)

### Open-Source References & Parsers:
- **RP-Portfolio (Crypto Tax & Portfolio Library)**:
  - Repository: `https://github.com/eprbell/rp-portfolio`
  - Reference File: `src/rp_portfolio/cointracking_parser.py`
  - Details: Verified positional indexing for repeated `Cur.` columns (`Cur.[0]` = Buy, `Cur.[1]` = Sell, `Cur.[2]` = Fee).
- **pquentin/cointracking-importer**:
  - Repository: `https://github.com/pquentin/cointracking-importer`
  - Details: Reference data mappings for CoinTracking Trade Table headers.

---

## 2. Coinbase CSV Format Sources

### Official Help Center & Developer Documentation:
- **Coinbase Help Center - How to Generate Reports**:
  - URL: [https://help.coinbase.com/en/coinbase/taxes/tools-reports/how-to-generate-reports](https://help.coinbase.com/en/coinbase/taxes/tools-reports/how-to-generate-reports)
  - Details: Documentation on generating the *Transaction History (CSV)* report, column structures, and preamble metadata lines.
- **Coinbase Taxes & Reports Portal**:
  - URL: [https://www.coinbase.com/reports](https://www.coinbase.com/reports)
- **Coinbase Developer Documentation (Cloud / CDP)**:
  - URL: [https://docs.cdp.coinbase.com/](https://docs.cdp.coinbase.com/)
- **Coinbase Pro / Advanced Trade Historical Reports Documentation**:
  - URL: [https://help.coinbase.com/en/pro/managing-my-account/account-information/account-history-reports](https://help.coinbase.com/en/pro/managing-my-account/account-information/account-history-reports)
  - Details: Definition of Coinbase Pro fill statements (`trade id,product,side,created at,size,price,fee,total`).

### Open-Source References & Parsers:
- **Rotki (Open Source Portfolio Tracker & Tax Calculator)**:
  - Repository: `https://github.com/rotki/rotki`
  - Reference Files: `rotkehlchen/exchanges/coinbase.py`, `rotkehlchen/csv_parsers.py`
  - Details: Tested handling of preamble rows in Coinbase retail exports and parsing of the `Total (inclusive of fees and/or spread)` and `Fees and/or Spread` columns.
- **cryptocpa/crypto-tax-calculator**:
  - Reference implementation for normalizing Coinbase transaction types (`Buy`, `Sell`, `Send`, `Receive`, `Convert`, `Rewards Income`).

---

## 3. Gemini CSV Format Sources

### Official Help Center & Developer Documentation:
- **Gemini Support - Transaction History & Account Statements**:
  - Article: *"How do I export my transaction history?"*
  - URL: [https://support.gemini.com/hc/en-us/articles/360001097866-How-do-I-export-my-transaction-history-](https://support.gemini.com/hc/en-us/articles/360001097866-How-do-I-export-my-transaction-history-)
  - Details: Instructions on generating ActiveTrader order execution history and general account transfer statements.
- **Gemini REST API Documentation - Past Trades / Fills**:
  - URL: [https://docs.gemini.com/rest-api/#get-past-trades](https://docs.gemini.com/rest-api/#get-past-trades)
  - Details: Structure of trade fills, basis points fee representation (`Trading Fee Rate (bps)`), fee calculation in USD, and net proceeds.

### Open-Source References & Parsers:
- **Rotki**:
  - Repository: `https://github.com/rotki/rotki`
  - Reference File: `rotkehlchen/exchanges/gemini.py`
  - Details: Handling dynamic column names for crypto asset amounts (e.g. `BTC Amount`, `ETH Amount`, or generic `Amount`).
- **bch/cointracking-gemini**:
  - Repository mapping Gemini ActiveTrader CSV fields to CoinTracking Trade Table schema.

---

## 4. Bittrex CSV Format Sources

### Official Historical Documentation & API References:
- **Bittrex Support Portal (Historical Knowledge Base)**:
  - Historical URL: `https://support.bittrex.com/hc/en-us/articles/115003723911-Exporting-Order-and-Transfer-History`
  - Details: Layout of Bittrex Orders CSV exports (`Uuid,Exchange,TimeStamp,OrderType,Limit,Quantity,QuantityRemaining,Commission,Price,PricePerUnit,Closed`) and Deposit/Withdrawal exports (`PaymentUuid,Currency,Amount,Address,Opened,Completed,TxCost,TxId`).
- **Bittrex API v3 Official Documentation (GitHub Archive)**:
  - URL: [https://bittrex.github.io/api/v3](https://bittrex.github.io/api/v3)
  - Details: Market naming convention specification (`QUOTE-BASE` e.g., `USD-BTC` where USD is the quote currency and BTC is the base asset traded).

### Open-Source References & Parsers:
- **Rotki**:
  - Repository: `https://github.com/rotki/rotki`
  - Reference File: `rotkehlchen/exchanges/bittrex.py`
  - Details: Verified that `Quantity` represents the executed base quantity, `Price` represents total quote spent/received, and `Commission` is paid in the quote currency.
- **pquentin/bittrex-to-cointracking**:
  - Reference script transforming Bittrex orders and funding CSVs into CoinTracking-compatible format.

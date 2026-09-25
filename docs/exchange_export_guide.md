# Exchange CSV Export Retrieval Guide

This guide provides step-by-step instructions on how to generate and download the raw CSV transaction reports from **CoinTracking**, **Coinbase**, **Gemini**, and **Bittrex**.

---

## 1. CoinTracking CSV Export

To export your recorded transactions from CoinTracking for reconciliation:

1. Log in to your [CoinTracking.info](https://cointracking.info) account.
2. In the top navigation menu, go to **Enter Coins** $\rightarrow$ **Overview & Manual Import** (or click directly on **Trade Table**).
3. If you only want to audit a specific exchange, click on the **Exchange** filter dropdown above the table and select the desired exchange (e.g., `Coinbase`, `Gemini`, or `Bittrex`). Alternatively, leave it as *All Exchanges* (the comparison tool can automatically filter by exchange).
4. At the top-right or bottom-right of the Trade Table, locate the **Export** buttons.
5. Click **CSV**.
6. Ensure that the exported file retains the standard column headers:
   - `Type`, `Buy`, `Cur.`, `Sell`, `Cur.`, `Fee`, `Cur.`, `Exchange`, `Group`, `Comment`, `Date`, `Tx-ID`
7. Save the file locally as `cointracking_export.csv`.

> [!TIP]
> Ensure the `Tx-ID` column is enabled in your table view prior to exporting. Including transaction/order IDs enables 100% deterministic Tier-1 matching.

---

## 2. Coinbase Export Reports

Coinbase offers two report styles depending on whether transactions were executed on Coinbase Consumer (Retail) or Coinbase Advanced / Pro.

### 2.1 Coinbase Consumer (Retail)
1. Log in to your account at [Coinbase.com](https://www.coinbase.com).
2. Click your profile avatar in the top right corner and select **Manage Account** or go directly to **Taxes & Reports** (or [coinbase.com/reports](https://www.coinbase.com/reports)).
3. In the **Reports** or **Activity** section, find **Transaction History**.
4. Click **Generate report**.
5. Select:
   - **Report type**: `CSV`
   - **Time range**: `All time` (or your specific tax year)
   - **Assets**: `All assets`
   - **Transaction types**: `All transactions`
6. Click **Generate Report**, wait a few seconds, then download the file.

> [!NOTE]
> Coinbase Consumer reports begin with 4 to 8 lines of preamble metadata (e.g., `Coinbase Reports`, user name, email, generated timestamp). This utility automatically detects and skips this metadata.

### 2.2 Coinbase Pro / Advanced Trade
1. Log in to [Coinbase Advanced](https://www.coinbase.com/advanced-trade) (or historical Coinbase Pro archives).
2. Go to **Orders** or **Fills** $\rightarrow$ **Statements / Reports**.
3. Under **Generate Statement**, choose **Fills**.
4. Set the date range and format to **CSV**.
5. Download the resulting file (which contains columns like `portfolio,trade id,product,side,created at,size,price,fee,total`).

---

## 3. Gemini Export Reports

Gemini separates trade executions from balance deposits and withdrawals.

### 3.1 ActiveTrader Order History (Trade Executions)
1. Log in to [Gemini.com](https://exchange.gemini.com).
2. Go to the **ActiveTrader** interface.
3. Click on **Account** (top right) $\rightarrow$ **Balances** or **Orders** $\rightarrow$ **History**.
4. Set the timeframe filter to the desired period (e.g., *Custom* $\rightarrow$ select start and end dates).
5. Click the **Export** or **Download CSV** button.
6. The file will contain:
   `Date,Time (UTC),Type,Symbol,Specification,Liquidity Indicator,Trading Fee Rate (bps),USD Amount,Trading Fee (USD),Net Proceeds (USD),<Crypto> Amount`

### 3.2 Account Transaction / Transfer History (Deposits & Withdrawals)
1. In the top navigation, click **Account** $\rightarrow$ **Transfer History** (or **Transaction History**).
2. Filter by `Deposits` and `Withdrawals`.
3. Click **Export to CSV**.
4. Save the file locally.

---

## 4. Bittrex Historical Exports

> [!NOTE]
> Bittrex U.S. ceased operations in 2023. If you are preparing historical tax returns (prior years or amended returns), you will be using previously downloaded CSV backups or records obtained from the Bittrex liquidation claims portal.

### 4.1 Orders History
- Historical exports downloaded from Bittrex Orders view:
  `Orders` $\rightarrow$ `Order History` $\rightarrow$ `Export CSV`
- Files contain headers:
  `Uuid,Exchange,TimeStamp,OrderType,Limit,Quantity,QuantityRemaining,Commission,Price,PricePerUnit,IsConditional,Condition,ConditionTarget,ImmediateOrCancel,Closed`

### 4.2 Deposits and Withdrawals
- Historical exports downloaded from Bittrex Holdings / Balances view:
  `Holdings` $\rightarrow$ `Deposits` / `Withdrawals` $\rightarrow$ `Export CSV`
- Files contain headers:
  `PaymentUuid,Currency,Amount,Address,Opened,Authorized,Pending,Completed,TxCost,TxId`

---

## 5. Summary Checklist Before Running the Comparator

- [ ] Export file is saved in plain `.csv` format (not `.xlsx`).
- [ ] For CoinTracking, ensure timestamps correspond to the same time range as the exchange report.
- [ ] If comparing a single exchange, verify that the exchange name in CoinTracking matches (e.g., `Coinbase` vs `Gemini` vs `Bittrex`).

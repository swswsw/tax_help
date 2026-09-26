# CoinTracking vs Exchange Tax Reconciliation Utility

A robust Python command-line utility and library designed to reconcile **CoinTracking** CSV exports against raw exchange reports (**Coinbase**, **Gemini**, and **Bittrex**) to identify duplicates, missing transactions, fee discrepancies, amount mismatches, and timezone drift.

---

## Features

- **Format Documentation**: Full documentation and reference schemas for CoinTracking, Coinbase (Retail & Pro), Gemini (ActiveTrader & Transfer History), and Bittrex (Orders & Transfers) in [`docs/format_specifications.md`](docs/format_specifications.md).
- **Format Auto-Detection**: Automatically identifies the exchange and CSV structure from header signatures.
- **Robust Parsing**:
  - Handles repeated headers like CoinTracking's triple `Cur.` columns.
  - Skips preamble lines in Coinbase Consumer exports.
  - Normalizes crypto tickers and currency representations (`XBT` -> `BTC`, `$3,200.00` -> `3200.00`).
  - Supports ISO-8601, US 12-hour AM/PM, and European date formats into unified UTC timestamps.
- **Reconciliation & Matching Engine**:
  - **Duplicate Detection**: Identifies internal duplicate imports in CoinTracking (e.g., duplicate API sync + CSV import) and exchange exports.
  - **Multi-Tier Matching**: Matches transactions by unique Order/Trade ID, or by fuzzy financial matching (matching assets, amounts within configurable tolerance %, and timestamps within configurable window).
  - **Timezone Offset Detection**: Automatically detects systematic integer-hour offsets (e.g. UTC vs local EDT/PST exports) and flags them rather than failing to match.
  - **Discrepancy Analysis**: Detects missing exchange fees in CoinTracking, fee currency mismatches, and gross vs net amount deviations.
  - **Missing Record Reporting**: Flags untracked exchange trades (missing in CoinTracking) and phantom entries (missing in exchange).
- **Multiple Output Formats**: Rich interactive console tables, clean JSON for downstream automation, or formatted GitHub Markdown.

## Documentation Guides

- [CSV Format Specifications (`docs/format_specifications.md`)](docs/format_specifications.md) — Exhaustive schema definitions, data types, and CSV examples for CoinTracking, Coinbase, Gemini, and Bittrex.
- [Documentation Sources & References (`docs/documentation_sources.md`)](docs/documentation_sources.md) — Official knowledge base links, developer API docs, and open-source references for all formats.
- [Exchange Export Retrieval Guide (`docs/exchange_export_guide.md`)](docs/exchange_export_guide.md) — Step-by-step instructions on navigating and downloading reports from each exchange.
- [Tax Reconciliation & Discrepancy Guide (`docs/reconciliation_guide.md`)](docs/reconciliation_guide.md) — Practical guide to crypto tax accounting, root causes of mismatches, and remediation workflows.
- [Architecture & Extensibility Guide (`docs/architecture.md`)](docs/architecture.md) — System design, matching algorithm details, and instructions for adding new exchange parsers.

---

## Directory Structure

```text
tax_help/
├── docs/
│   ├── format_specifications.md    # Detailed specifications and row examples
│   ├── documentation_sources.md    # Official links and reference sources
│   ├── exchange_export_guide.md    # Step-by-step export download instructions
│   ├── reconciliation_guide.md     # In-depth tax reconciliation & issue fixing guide
│   └── architecture.md             # System design & developer guide
├── sample_data/                    # Sample CSV datasets (see sample_data/README.md)
│   ├── cointracking_sample.csv
│   ├── cointracking_custom_import_sample.csv
│   ├── coinbase_retail_sample.csv
│   ├── coinbase_pro_sample.csv
│   ├── coinbase_advanced_fills_sample.csv
│   ├── gemini_sample.csv
│   ├── gemini_transfers_sample.csv
│   ├── bittrex_sample.csv
│   └── bittrex_transfers_sample.csv
├── tax_comparator/                 # Core Python package
│   ├── models.py                   # Data models (NormalizedTransaction, Discrepancy, etc.)
│   ├── comparator.py               # Matching & reconciliation engine
│   ├── reporter.py                 # Console, Markdown, and JSON formatters
│   ├── cli.py                      # Command-line interface
│   └── parsers/
│       ├── base.py                 # Base parser, timestamp & number cleaners
│       ├── cointracking.py         # CoinTracking Trade Table parser
│       ├── coinbase.py             # Coinbase Consumer & Pro parser
│       ├── gemini.py               # Gemini ActiveTrader & transfers parser
│       └── bittrex.py              # Bittrex orders & transfers parser
├── tests/                          # Test suite (unittest)
│   ├── test_parsers.py
│   ├── test_comparator.py
│   └── test_cli.py
├── requirements.txt
└── README.md
```

---

## Usage

### 1. Basic Comparison (Auto-Detect Exchange)

```bash
python3 -m tax_comparator.cli -c sample_data/cointracking_sample.csv -e sample_data/coinbase_retail_sample.csv
```

### 2. Explicit Exchange Specification

```bash
# Compare against Coinbase
python3 -m tax_comparator.cli -c sample_data/cointracking_sample.csv -e sample_data/coinbase_retail_sample.csv -x coinbase

# Compare against Gemini
python3 -m tax_comparator.cli -c sample_data/cointracking_sample.csv -e sample_data/gemini_sample.csv -x gemini

# Compare against Bittrex
python3 -m tax_comparator.cli -c sample_data/cointracking_sample.csv -e sample_data/bittrex_sample.csv -x bittrex
```

### 3. Generate JSON or Markdown Reports

```bash
# Export report as Markdown
python3 -m tax_comparator.cli -c cointracking.csv -e coinbase.csv -f markdown -o report.md

# Export report as JSON for programmatic analysis
python3 -m tax_comparator.cli -c cointracking.csv -e gemini.csv -f json -o report.json
```

### 4. Custom Tolerances

```bash
# Adjust time matching window to 300 seconds and amount tolerance to 0.1%
python3 -m tax_comparator.cli -c cointracking.csv -e coinbase.csv -t 300 -a 0.1
```

---

## CLI Options

| Flag | Name | Default | Description |
| :--- | :--- | :--- | :--- |
| `-c` | `--cointracking` | *(Required)* | Path to CoinTracking export CSV file |
| `-e` | `--exchange-file` | *(Required)* | Path to Exchange export CSV file |
| `-x` | `--exchange` | `auto` | Exchange name (`coinbase`, `gemini`, `bittrex`) |
| `-t` | `--time-tolerance`| `120` | Matching time window in seconds |
| `-a` | `--amount-tolerance`| `0.05` | Numerical percent tolerance for rounding differences |
| `--no-tz-detection` | | `False` | Disable automatic detection of integer-hour timezone offsets |
| `-f` | `--format` | `console` | Report format: `console`, `json`, or `markdown` |
| `-o` | `--output` | `None` | Output file destination |

---

## Running Tests

Run the complete test suite:

```bash
python3 -m unittest discover -s tests -v
```

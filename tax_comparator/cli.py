"""Command Line Interface for the CoinTracking & Exchange Report Comparator."""

import argparse
from pathlib import Path
import sys

from tax_comparator.comparator import TaxComparator
from tax_comparator.parsers import CoinTrackingParser, get_parser
from tax_comparator.reporter import ReportFormatter


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare CoinTracking export CSVs with exchange reports (Coinbase, Gemini, Bittrex) for duplicates and inconsistencies.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-c",
        "--cointracking",
        required=True,
        type=Path,
        help="Path to the CoinTracking CSV export file",
    )
    parser.add_argument(
        "-e",
        "--exchange-file",
        required=True,
        type=Path,
        help="Path to the Exchange export CSV file (Coinbase, Gemini, or Bittrex)",
    )
    parser.add_argument(
        "-x",
        "--exchange",
        choices=["coinbase", "gemini", "bittrex"],
        help="Exchange name. If omitted, the tool attempts to auto-detect from file structure.",
    )
    parser.add_argument(
        "-t",
        "--time-tolerance",
        type=int,
        default=120,
        help="Matching tolerance window in seconds (default: 120s)",
    )
    parser.add_argument(
        "-a",
        "--amount-tolerance",
        type=float,
        default=0.05,
        help="Amount percentage tolerance for floating point / rounding differences (default: 0.05%%)",
    )
    parser.add_argument(
        "--no-tz-detection",
        action="store_true",
        help="Disable automatic detection of integer-hour timezone offsets",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["console", "json", "markdown"],
        default="console",
        help="Report output format (default: console)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Optional destination file path to save the generated report",
    )

    args = parser.parse_args()

    # Validate file existence
    if not args.cointracking.exists():
        print(f"Error: CoinTracking file not found: {args.cointracking}", file=sys.stderr)
        return 2

    if not args.exchange_file.exists():
        print(f"Error: Exchange file not found: {args.exchange_file}", file=sys.stderr)
        return 2

    # Instantiate exchange parser
    try:
        ex_parser = get_parser(exchange_name=args.exchange, file_path=args.exchange_file)
        exchange_name = getattr(ex_parser, "EXCHANGE_NAME", args.exchange or "Exchange")
    except Exception as err:
        print(f"Error initializing exchange parser: {err}", file=sys.stderr)
        return 2

    # Parse exchange records
    try:
        ex_txs = ex_parser.parse_file(args.exchange_file)
    except Exception as err:
        print(f"Error parsing exchange file '{args.exchange_file}': {err}", file=sys.stderr)
        return 2

    # Parse CoinTracking records (filtered by exchange name)
    try:
        ct_parser = CoinTrackingParser(filter_exchange=exchange_name)
        ct_txs = ct_parser.parse_file(args.cointracking)
    except Exception as err:
        print(f"Error parsing CoinTracking file '{args.cointracking}': {err}", file=sys.stderr)
        return 2

    # Run comparison
    comparator = TaxComparator(
        time_tolerance_seconds=args.time_tolerance,
        amount_tolerance_percent=args.amount_tolerance,
        detect_timezone_offsets=not args.no_tz_detection,
    )

    report = comparator.compare(
        cointracking_txs=ct_txs,
        exchange_txs=ex_txs,
        exchange_name=exchange_name,
        ct_file_name=args.cointracking.name,
        ex_file_name=args.exchange_file.name,
    )

    formatter = ReportFormatter(report)

    # Output results
    if args.format == "console":
        formatter.print_console()
    elif args.format == "json":
        out = formatter.to_json()
        if args.output:
            args.output.write_text(out, encoding="utf-8")
            print(f"JSON report saved to {args.output}")
        else:
            print(out)
    elif args.format == "markdown":
        out = formatter.to_markdown()
        if args.output:
            args.output.write_text(out, encoding="utf-8")
            print(f"Markdown report saved to {args.output}")
        else:
            print(out)

    if args.output and args.format == "console":
        # Also save markdown if output path is provided with console mode
        args.output.write_text(formatter.to_markdown(), encoding="utf-8")
        print(f"Report also written to {args.output}")

    # Return exit code: 0 if clean, 1 if discrepancies / duplicates / missing found
    has_issues = bool(
        report.cointracking_duplicates
        or report.missing_in_cointracking
        or report.missing_in_exchange
        or report.matched_with_discrepancies_count > 0
    )
    return 1 if has_issues else 0


if __name__ == "__main__":
    sys.exit(main())

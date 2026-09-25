"""Generates console output, JSON, and Markdown comparison reports."""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from tax_comparator.models import ComparisonReport, DiscrepancyType

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class ReportFormatter:
    """Formats ComparisonReport objects into various output media."""

    def __init__(self, report: ComparisonReport):
        self.report = report

    def print_console(self) -> None:
        if RICH_AVAILABLE:
            self._print_rich_console()
        else:
            self._print_plain_console()

    def _print_rich_console(self) -> None:
        console = Console()
        r = self.report

        console.print()
        console.print(
            Panel(
                f"[bold cyan]CoinTracking vs {r.exchange_name.upper()} Reconciliation Report[/bold cyan]\n"
                f"[dim]CoinTracking File: {r.cointracking_file}\n"
                f"Exchange File:     {r.exchange_file}[/dim]",
                title="Tax Comparator",
                border_style="cyan",
            )
        )

        # Overview Table
        table = Table(title="Reconciliation Summary", border_style="dim")
        table.add_column("Category", style="bold")
        table.add_column("Count", justify="right")
        table.add_column("Status", justify="center")

        table.add_row("Total CoinTracking Records", str(r.total_cointracking_records), "ℹ️")
        table.add_row(f"Total {r.exchange_name} Records", str(r.total_exchange_records), "ℹ️")
        table.add_row("Exact Matches", str(r.exact_matches_count), "[green]PASS[/green]")
        table.add_row("Matched with Discrepancies", str(r.matched_with_discrepancies_count), "[yellow]WARN[/yellow]" if r.matched_with_discrepancies_count > 0 else "[green]OK[/green]")
        table.add_row("CoinTracking Internal Duplicates", str(len(r.cointracking_duplicates)), "[red]FAIL[/red]" if r.cointracking_duplicates else "[green]OK[/green]")
        table.add_row(f"{r.exchange_name} Internal Duplicates", str(len(r.exchange_duplicates)), "[yellow]WARN[/yellow]" if r.exchange_duplicates else "[green]OK[/green]")
        table.add_row("Missing in CoinTracking (Untracked)", str(len(r.missing_in_cointracking)), "[red]FAIL[/red]" if r.missing_in_cointracking else "[green]OK[/green]")
        table.add_row("Missing in Exchange (Ghost Records)", str(len(r.missing_in_exchange)), "[red]FAIL[/red]" if r.missing_in_exchange else "[green]OK[/green]")

        console.print(table)
        console.print()

        # Print Details if any issues exist
        if r.cointracking_duplicates:
            console.print("[bold red]🚨 CoinTracking Internal Duplicates Detected:[/bold red]")
            for i, group in enumerate(r.cointracking_duplicates, 1):
                lines = ", ".join(f"Line {tx.source_line}" for tx in group)
                console.print(f"  {i}. {group[0].summary_str()} -> Present at {lines}")
            console.print()

        if r.missing_in_cointracking:
            console.print(f"[bold red]❌ Missing in CoinTracking (Found in {r.exchange_name}):[/bold red]")
            for i, tx in enumerate(r.missing_in_cointracking, 1):
                console.print(f"  {i}. [Exchange Line {tx.source_line}] {tx.summary_str()}")
            console.print()

        if r.missing_in_exchange:
            console.print(f"[bold red]❌ Missing in {r.exchange_name} (Found in CoinTracking):[/bold red]")
            for i, tx in enumerate(r.missing_in_exchange, 1):
                console.print(f"  {i}. [CT Line {tx.source_line}] {tx.summary_str()}")
            console.print()

        discrepancies_by_type = {}
        for pair in r.matched_pairs:
            for disc in pair.discrepancies:
                discrepancies_by_type.setdefault(disc.discrepancy_type.value, []).append((pair, disc))

        if discrepancies_by_type:
            console.print("[bold yellow]⚠️  Discrepancies on Matched Transactions:[/bold yellow]")
            for dtype, items in discrepancies_by_type.items():
                console.print(f"  [bold cyan]• {dtype}:[/bold cyan] ({len(items)} instances)")
                for pair, disc in items[:10]:  # Cap at 10 for terminal readability
                    console.print(f"    - [CT L:{pair.ct_tx.source_line} / EX L:{pair.exchange_tx.source_line}]: {disc.message}")
                if len(items) > 10:
                    console.print(f"    ... and {len(items) - 10} more.")
            console.print()

    def _print_plain_console(self) -> None:
        r = self.report
        print("=" * 70)
        print(f"CoinTracking vs {r.exchange_name.upper()} Reconciliation Report")
        print(f"CoinTracking File: {r.cointracking_file}")
        print(f"Exchange File:     {r.exchange_file}")
        print("-" * 70)
        print(f"Total CoinTracking Records:       {r.total_cointracking_records}")
        print(f"Total {r.exchange_name} Records:          {r.total_exchange_records}")
        print(f"Exact Matches:                    {r.exact_matches_count}")
        print(f"Matched with Discrepancies:       {r.matched_with_discrepancies_count}")
        print(f"CoinTracking Duplicates:          {len(r.cointracking_duplicates)}")
        print(f"Exchange Duplicates:              {len(r.exchange_duplicates)}")
        print(f"Missing in CoinTracking:          {len(r.missing_in_cointracking)}")
        print(f"Missing in Exchange:              {len(r.missing_in_exchange)}")
        print("=" * 70)

        if r.cointracking_duplicates:
            print("\n--- COINTRACKING INTERNAL DUPLICATES ---")
            for i, group in enumerate(r.cointracking_duplicates, 1):
                lines = ", ".join(f"Line {tx.source_line}" for tx in group)
                print(f"{i}. {group[0].summary_str()} (Lines: {lines})")

        if r.missing_in_cointracking:
            print(f"\n--- MISSING IN COINTRACKING (EXCHANGE RECORDS) ---")
            for i, tx in enumerate(r.missing_in_cointracking, 1):
                print(f"{i}. [Line {tx.source_line}] {tx.summary_str()}")

        if r.missing_in_exchange:
            print(f"\n--- MISSING IN EXCHANGE (COINTRACKING RECORDS) ---")
            for i, tx in enumerate(r.missing_in_exchange, 1):
                print(f"{i}. [Line {tx.source_line}] {tx.summary_str()}")

        discrepancies = [d for p in r.matched_pairs for d in p.discrepancies]
        if discrepancies:
            print(f"\n--- DISCREPANCIES ON MATCHED PAIRS ({len(discrepancies)}) ---")
            for i, d in enumerate(discrepancies[:20], 1):
                print(f"{i}. [{d.severity}] {d.message}")
            if len(discrepancies) > 20:
                print(f"... and {len(discrepancies) - 20} more.")

    def to_json(self) -> str:
        r = self.report
        data = {
            "exchange": r.exchange_name,
            "cointracking_file": r.cointracking_file,
            "exchange_file": r.exchange_file,
            "summary": {
                "total_cointracking_records": r.total_cointracking_records,
                "total_exchange_records": r.total_exchange_records,
                "exact_matches": r.exact_matches_count,
                "matched_with_discrepancies": r.matched_with_discrepancies_count,
                "cointracking_duplicate_groups": len(r.cointracking_duplicates),
                "exchange_duplicate_groups": len(r.exchange_duplicates),
                "missing_in_cointracking": len(r.missing_in_cointracking),
                "missing_in_exchange": len(r.missing_in_exchange),
                "total_discrepancies": len(r.discrepancies),
            },
            "cointracking_duplicates": [
                [{"line": tx.source_line, "summary": tx.summary_str(), "order_id": tx.order_id} for tx in group]
                for group in r.cointracking_duplicates
            ],
            "missing_in_cointracking": [
                {"line": tx.source_line, "summary": tx.summary_str(), "order_id": tx.order_id}
                for tx in r.missing_in_cointracking
            ],
            "missing_in_exchange": [
                {"line": tx.source_line, "summary": tx.summary_str(), "order_id": tx.order_id}
                for tx in r.missing_in_exchange
            ],
            "discrepancies": [
                {
                    "type": d.discrepancy_type.value,
                    "severity": d.severity,
                    "message": d.message,
                    "ct_line": d.ct_tx.source_line if d.ct_tx else None,
                    "exchange_line": d.exchange_tx.source_line if d.exchange_tx else None,
                    "details": d.details,
                }
                for d in r.discrepancies
            ],
        }
        return json.dumps(data, indent=2, default=str)

    def to_markdown(self) -> str:
        r = self.report
        md = [
            f"# CoinTracking vs {r.exchange_name} Reconciliation Report",
            "",
            f"- **CoinTracking Export File**: `{r.cointracking_file}`",
            f"- **Exchange Report File**: `{r.exchange_file}`",
            "",
            "## Summary",
            "",
            "| Metric | Value | Status |",
            "| :--- | :---: | :---: |",
            f"| Total CoinTracking Records | {r.total_cointracking_records} | ℹ️ |",
            f"| Total {r.exchange_name} Records | {r.total_exchange_records} | ℹ️ |",
            f"| Exact Matches | {r.exact_matches_count} | ✅ PASS |",
            f"| Matched with Discrepancies | {r.matched_with_discrepancies_count} | ⚠️ WARN |",
            f"| CoinTracking Duplicate Groups | {len(r.cointracking_duplicates)} | {'❌ FAIL' if r.cointracking_duplicates else '✅ OK'} |",
            f"| Missing in CoinTracking | {len(r.missing_in_cointracking)} | {'❌ FAIL' if r.missing_in_cointracking else '✅ OK'} |",
            f"| Missing in Exchange | {len(r.missing_in_exchange)} | {'❌ FAIL' if r.missing_in_exchange else '✅ OK'} |",
            "",
        ]

        if r.cointracking_duplicates:
            md.extend([
                "## CoinTracking Internal Duplicates",
                "",
                "The following transactions appear multiple times in your CoinTracking export:",
                "",
            ])
            for i, group in enumerate(r.cointracking_duplicates, 1):
                lines = ", ".join(f"`Line {tx.source_line}`" for tx in group)
                md.append(f"{i}. **{group[0].summary_str()}** (Found on {lines})")
            md.append("")

        if r.missing_in_cointracking:
            md.extend([
                "## Missing in CoinTracking (Present in Exchange)",
                "",
                "These transactions exist in the exchange report but have not been imported into CoinTracking:",
                "",
                "| Exchange Line | Timestamp (UTC) | Type | Details | ID |",
                "| :---: | :--- | :--- | :--- | :--- |",
            ])
            for tx in r.missing_in_cointracking:
                details = f"+{tx.received_amount or ''} {tx.received_currency or ''} -{tx.sent_amount or ''} {tx.sent_currency or ''}".strip()
                md.append(f"| {tx.source_line} | {tx.timestamp.strftime('%Y-%m-%d %H:%M:%S')} | {tx.tx_type.value} | {details} | {tx.order_id or '-'} |")
            md.append("")

        if r.missing_in_exchange:
            md.extend([
                "## Missing in Exchange (Present in CoinTracking)",
                "",
                "These transactions are logged in CoinTracking as being on this exchange, but could not be found in the exchange export:",
                "",
                "| CT Line | Timestamp | Type | Details | ID |",
                "| :---: | :--- | :--- | :--- | :--- |",
            ])
            for tx in r.missing_in_exchange:
                details = f"+{tx.received_amount or ''} {tx.received_currency or ''} -{tx.sent_amount or ''} {tx.sent_currency or ''}".strip()
                md.append(f"| {tx.source_line} | {tx.timestamp.strftime('%Y-%m-%d %H:%M:%S')} | {tx.tx_type.value} | {details} | {tx.order_id or '-'} |")
            md.append("")

        if r.discrepancies:
            md.extend([
                "## Discrepancies and Inconsistencies",
                "",
                "| Severity | Issue Type | Description |",
                "| :---: | :--- | :--- |",
            ])
            for d in r.discrepancies:
                md.append(f"| **{d.severity}** | `{d.discrepancy_type.value}` | {d.message} |")
            md.append("")

        return "\n".join(md)

"""Unit tests for the CLI entry point."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tax_comparator.cli import main

SAMPLE_DIR = Path(__file__).parent.parent / "sample_data"


class TestCLI(unittest.TestCase):

    def test_cli_coinbase_json_output(self):
        ct_file = str(SAMPLE_DIR / "cointracking_sample.csv")
        cb_file = str(SAMPLE_DIR / "coinbase_retail_sample.csv")

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            test_args = [
                "tax_comparator",
                "-c", ct_file,
                "-e", cb_file,
                "-x", "coinbase",
                "-f", "json",
                "-o", str(tmp_path),
            ]
            with patch("sys.argv", test_args):
                exit_code = main()
                # Should exit with 1 because discrepancies/duplicates were found
                self.assertEqual(exit_code, 1)

            # Verify JSON file content
            content = json.loads(tmp_path.read_text(encoding="utf-8"))
            self.assertEqual(content["exchange"], "Coinbase")
            self.assertEqual(content["summary"]["cointracking_duplicate_groups"], 1)
            self.assertEqual(content["summary"]["missing_in_cointracking"], 1)
            self.assertEqual(content["summary"]["missing_in_exchange"], 1)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_cli_gemini_markdown_output(self):
        ct_file = str(SAMPLE_DIR / "cointracking_sample.csv")
        gem_file = str(SAMPLE_DIR / "gemini_sample.csv")

        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            test_args = [
                "tax_comparator",
                "-c", ct_file,
                "-e", gem_file,
                "-x", "gemini",
                "-f", "markdown",
                "-o", str(tmp_path),
            ]
            with patch("sys.argv", test_args):
                exit_code = main()
                self.assertEqual(exit_code, 1)

            md_content = tmp_path.read_text(encoding="utf-8")
            self.assertIn("CoinTracking vs Gemini Reconciliation Report", md_content)
            self.assertIn("Missing in CoinTracking", md_content)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_cli_missing_file_error(self):
        test_args = [
            "tax_comparator",
            "-c", "non_existent_file.csv",
            "-e", str(SAMPLE_DIR / "coinbase_retail_sample.csv"),
        ]
        with patch("sys.argv", test_args):
            exit_code = main()
            self.assertEqual(exit_code, 2)


if __name__ == "__main__":
    unittest.main()

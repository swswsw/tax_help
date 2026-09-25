"""Parser registry and auto-detection factory."""

from pathlib import Path
from typing import Optional, Type

from tax_comparator.parsers.base import BaseParser
from tax_comparator.parsers.bittrex import BittrexParser
from tax_comparator.parsers.coinbase import CoinbaseParser
from tax_comparator.parsers.cointracking import CoinTrackingParser
from tax_comparator.parsers.gemini import GeminiParser

PARSER_REGISTRY = {
    "cointracking": CoinTrackingParser,
    "coinbase": CoinbaseParser,
    "gemini": GeminiParser,
    "gemini.com": GeminiParser,
    "bittrex": BittrexParser,
    "bitrex": BittrexParser,
}


def get_parser(exchange_name: Optional[str] = None, file_path: Optional[Path] = None) -> BaseParser:
    """Returns an instantiated parser based on exchange name or auto-detection."""
    if exchange_name:
        clean_name = exchange_name.lower().strip()
        parser_cls = PARSER_REGISTRY.get(clean_name)
        if parser_cls:
            return parser_cls()
        raise ValueError(
            f"Unsupported exchange '{exchange_name}'. Supported options: coinbase, gemini, bittrex, cointracking."
        )

    if file_path:
        for name, cls in [
            ("coinbase", CoinbaseParser),
            ("gemini", GeminiParser),
            ("bittrex", BittrexParser),
            ("cointracking", CoinTrackingParser),
        ]:
            if cls.can_parse(file_path):
                return cls()

    raise ValueError(
        f"Could not automatically detect the format of '{file_path}'. Please specify --exchange (coinbase, gemini, bittrex)."
    )


__all__ = [
    "BaseParser",
    "CoinTrackingParser",
    "CoinbaseParser",
    "GeminiParser",
    "BittrexParser",
    "get_parser",
]

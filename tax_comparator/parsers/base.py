"""Base parser class with robust timestamp, numeric, and currency cleaning helpers."""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
from typing import List, Optional

from tax_comparator.models import NormalizedTransaction


class BaseParser(ABC):
    """Abstract base class for all exchange and tracking CSV parsers."""

    CURRENCY_ALIASES = {
        "XBT": "BTC",
        "XDG": "DOGE",
        "BCHABC": "BCH",
        "BCC": "BCH",
        "STR": "XLM",
    }

    @abstractmethod
    def parse_file(self, file_path: Path) -> List[NormalizedTransaction]:
        """Parses the CSV file into a list of NormalizedTransaction objects."""
        pass

    @classmethod
    @abstractmethod
    def can_parse(cls, file_path: Path) -> bool:
        """Determines if this parser handles the given file format."""
        pass

    @staticmethod
    def clean_string(val: Optional[str]) -> str:
        if val is None:
            return ""
        return val.strip().strip('"').strip("'").strip().strip("\ufeff")

    @classmethod
    def normalize_currency(cls, curr: Optional[str]) -> Optional[str]:
        if not curr:
            return None
        cleaned = curr.strip().upper()
        if not cleaned:
            return None
        # Remove unwanted punctuation
        cleaned = re.sub(r"[^A-Z0-9_\-]", "", cleaned)
        return cls.CURRENCY_ALIASES.get(cleaned, cleaned)

    @staticmethod
    def parse_decimal(val: Optional[str]) -> Optional[Decimal]:
        if not val:
            return None
        cleaned = val.strip().replace("$", "").replace("€", "").replace("£", "").replace(",", "").strip()
        if not cleaned or cleaned.lower() in ("none", "null", "nan", "-"):
            return None
        
        # Handle parentheses for negative numbers, e.g. (15.00) -> -15.00
        if cleaned.startswith("(") and cleaned.endswith(")"):
            cleaned = f"-{cleaned[1:-1]}"
            
        try:
            d = Decimal(cleaned)
            return abs(d)  # Return magnitude; direction is tracked by leg
        except InvalidOperation:
            return None

    @staticmethod
    def parse_timestamp(val: Optional[str]) -> Optional[datetime]:
        """Parses various date/time formats into UTC timezone-aware datetime."""
        if not val:
            return None
        cleaned = val.strip().replace(" UTC", "").replace("Z", "+00:00")
        
        # ISO format: 2021-05-10T14:23:05 or 2021-05-10T14:23:05+00:00
        try:
            dt = datetime.fromisoformat(cleaned)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            return dt
        except ValueError:
            pass

        # Formats to attempt
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y/%m/%d %H:%M:%S",
            "%d.%m.%Y %H:%M:%S",
            "%d.%m.%Y %H:%M",
            "%m/%d/%Y %H:%M:%S",
            "%m/%d/%Y %I:%M:%S %p",
            "%m/%d/%Y %I:%M %p",
            "%m/%d/%y %H:%M:%S",
            "%m/%d/%y %I:%M:%S %p",
            "%d/%m/%Y %H:%M:%S",
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(cleaned, fmt)
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
                
        # Regex matching for loose date times
        m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})\s+(\d{1,2}):(\d{1,2}):(\d{1,2})\s*([APap][Mm])?$", cleaned)
        if m:
            month, day, year, hour, minute, second, ampm = m.groups()
            h = int(hour)
            if ampm:
                if ampm.upper() == "PM" and h < 12:
                    h += 12
                elif ampm.upper() == "AM" and h == 12:
                    h = 0
            dt = datetime(int(year), int(month), int(day), h, int(minute), int(second), tzinfo=timezone.utc)
            return dt

        return None

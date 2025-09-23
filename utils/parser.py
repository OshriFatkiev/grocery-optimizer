"""
parser.py
---------
String cleaning and price-parsing utilities.
"""

import re
from typing import Optional


def clean_item_name(name: str) -> str:
    """
    Normalize an item name: trim whitespace, collapse multiple spaces.
    """
    return re.sub(r"\s+", " ", name).strip()


def parse_price(price_str: str) -> Optional[float]:
    """
    Convert a price string like '12.90 ₪' or '₪12.9*' to a float.
    Returns None if it cannot be parsed.
    """
    if not price_str:
        return None
    # Remove currency symbols, asterisks, RTL markers, etc.
    clean = re.sub(r"[^\d.,]", "", price_str)
    clean = clean.replace(",", ".")
    try:
        return float(clean)
    except ValueError:
        return None

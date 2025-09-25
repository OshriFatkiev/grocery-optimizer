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


def all_words_hebrew(file_path: str) -> bool:
    """
    Check that every word in the given text file contains only Hebrew letters.

    Args:
        file_path: Path to the .txt file.

    Returns:
        True if all words are Hebrew-only, False otherwise.
    """
    hebrew_word_pattern = re.compile(r"^[\u0590-\u05FF]+$")

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            for word in line.split():
                # strip common punctuation from the ends
                word_clean = word.strip(".,!?;:\"'()[]{}")
                if word_clean and not hebrew_word_pattern.fullmatch(word_clean):
                    print(
                        f"Found non-Hebrew word: {word_clean}. Grocery list most contain only items in Hebrew!"
                    )
                    return False
    return True

"""
supermarket_scraper.py
----------------------
Site-specific scraper for chp.co.il price comparisons.
"""

import re
from typing import Dict, List, Optional, Sequence, Tuple

from bs4 import BeautifulSoup

from utils.parser import parse_price
from .base_scraper import BaseScraper


class SupermarketScraper(BaseScraper):
    """
    Encapsulates all scraping logic for chp.co.il:
    * fetch product barcode by name
    * fetch price comparison table for that barcode
    """

    SHUFERSAL_LABEL = "שופרסל"
    _STORE_HEADER_CANDIDATES = (
        "רשת",
        "שם סניף",
        "שם הסניף",
        "סניף",
        "חנות",
        "שם חנות",
        "שם החנות",
        "store",
    )
    _PRICE_HEADER_KEYWORDS = (
        "מחיר",
        "מבצע",
        "עלות",
        "תשלום",
        "price",
        "cost",
    )

    def __init__(
        self, city_id: int = 3616, street_id: int = 9000, city: str = "מעלה אדומים"
    ):
        # Base URL isn't required since we pass absolute URLs,
        # but you can set it if you like: base_url="https://chp.co.il"
        super().__init__()
        self.city_id = city_id
        self.street_id = street_id
        self.city = city

    # ------------------------------------------------------------------
    def find_barcode(self, item_name: str) -> Optional[str]:
        """
        Look up the product barcode for the given item name.
        Returns None if no match is found.
        """
        params = {
            "term": item_name,
            "from": 0,
            "u": "0.5238",  # site seems to require this param; random float is okay
            "shopping_address": self.city,
            "shopping_address_city_id": self.city_id,
            "shopping_address_street_id": self.street_id,
        }
        resp = self.get(
            "https://chp.co.il/autocompletion/product_extended", params=params
        )
        data = resp.json()

        if not data:
            return None
        # First result is best match; ID looks like "product_<barcode>"
        return data[0]["id"]

    # ------------------------------------------------------------------
    def compare_prices(
        self, product_barcode: str
    ) -> Tuple[List[Dict[str, str]], List[str]]:
        """
        Given a product barcode, fetch the comparison table.

        Returns:
            Tuple containing the list of store rows and the header names.
        """
        params = {
            "shopping_address": self.city,
            "shopping_address_city_id": self.city_id,
            "shopping_address_street_id": self.street_id,
            "product_barcode": product_barcode,
            "from": 0,
            "num_results": 20,
        }
        resp = self.get("https://chp.co.il/main_page/compare_results", params=params)
        soup = BeautifulSoup(resp.text, "html.parser")

        stores: List[Dict[str, str]] = []
        headers: List[str] = []

        for row in soup.select("table tr"):
            header_cells = row.find_all("th")
            if header_cells:
                headers = [cell.get_text(strip=True) for cell in header_cells]
                continue

            data_cells = row.find_all("td")
            if not data_cells:
                continue

            values = [cell.get_text(strip=True) for cell in data_cells]
            if headers and len(values) == len(headers):
                stores.append(dict(zip(headers, values)))
            elif values:
                stores.append({str(idx): value for idx, value in enumerate(values)})

        return stores, headers

    # ------------------------------------------------------------------
    def _looks_like_price(self, value: str) -> bool:
        if not value:
            return False
        stripped = value.strip()
        if not stripped:
            return False

        cleaned = stripped
        currency_tokens = [
            "₪",
            "ש\"ח",
            "ש״ח",
            "שח",
            "NIS",
            "ILS",
            "תשלום",
            "כולל מע\"מ",
        ]
        for token in currency_tokens:
            cleaned = cleaned.replace(token, "")

        cleaned = re.sub(r"[0-9.,]", "", cleaned)
        cleaned = cleaned.replace(" ", "").replace("*", "").replace("/", "")
        return cleaned == ""

    # ------------------------------------------------------------------
    def _price_columns(self, row: Dict[str, str]) -> List[str]:
        columns: List[str] = []
        for key, value in row.items():
            if not value:
                continue
            lowered = key.lower()
            if any(keyword in lowered for keyword in self._PRICE_HEADER_KEYWORDS):
                columns.append(key)
                continue
            if self._looks_like_price(value):
                columns.append(key)
        return columns

    # ------------------------------------------------------------------
    def _select_store_header(self, headers: Sequence[str]) -> Optional[str]:
        for candidate in self._STORE_HEADER_CANDIDATES:
            for header in headers:
                if candidate.lower() in header.lower():
                    return header
        return headers[0] if headers else None

    # ------------------------------------------------------------------
    def _extract_store_name(
        self,
        row: Dict[str, str],
        headers: Sequence[str],
        price_columns: Sequence[str],
    ) -> Optional[str]:
        header = self._select_store_header(headers)
        if header:
            value = row.get(header)
            if isinstance(value, str) and value.strip():
                return value.strip()

        for key in row.keys():
            if key in price_columns:
                continue
            value = row.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        return None

    # ------------------------------------------------------------------
    def _extract_price(
        self, row: Dict[str, str], price_columns: Sequence[str]
    ) -> Optional[str]:
        """
        Helper to extract the actual price from a row.
        Prioritizes sale price columns (containing 'מבצע') if present.
        """
        for key in price_columns:
            if "מבצע" in key:
                value = row.get(key)
                if value:
                    return value.strip("* ").strip()

        for key in price_columns:
            value = row.get(key)
            if value:
                return value.strip("* ").strip()

        return None

    def get_prices(
        self, item_name: str
    ) -> Optional[Dict[str, Optional[Dict[str, str]]]]:
        """
        Fetch all prices for an item and return both best price and Shufersal price.

        Returns:
            Dict with keys:
              * 'best'
              * 'shufersal'
              * 'stores' - list of dicts with keys store/price/raw_row
        """
        barcode = self.find_barcode(item_name)
        if not barcode:
            return None

        rows, headers = self.compare_prices(barcode)
        if not rows:
            return None

        data_rows = rows[1:] if len(rows) > 1 else rows

        store_entries: List[Dict[str, object]] = []
        for row in data_rows:
            price_columns = self._price_columns(row)
            if not price_columns:
                continue

            price_str = self._extract_price(row, price_columns)
            if not price_str:
                continue

            store_name = self._extract_store_name(row, headers, price_columns)
            if not store_name:
                continue

            price_value = parse_price(price_str)
            if price_value is None:
                continue

            store_entries.append(
                {
                    "store": store_name,
                    "price": price_str,
                    "price_value": price_value,
                    "raw_row": row,
                }
            )

        if not store_entries:
            return None

        store_entries.sort(key=lambda entry: entry["price_value"])
        best_entry = store_entries[0]
        best_price = {
            "store": best_entry["store"],
            "price": best_entry["price"],
            "raw_row": best_entry["raw_row"],
        }

        shufersal_entry = next(
            (
                entry
                for entry in store_entries
                if self.SHUFERSAL_LABEL in str(entry["store"])
            ),
            None,
        )
        shufersal_price = (
            {
                "store": shufersal_entry["store"],
                "price": shufersal_entry["price"],
                "price_value": shufersal_entry["price_value"],
                "raw_row": shufersal_entry["raw_row"],
            }
            if shufersal_entry
            else None
        )

        return {
            "best": best_price,
            "shufersal": shufersal_price,
            "stores": store_entries,
        }

    # ------------------------------------------------------------------
    def best_price(self, item_name: str) -> Optional[Dict[str, str]]:
        """
        Convenience helper: find the single best price for an item.
        Returns dict with keys: 'store', 'price', 'raw_row' or None.
        """
        result = self.get_prices(item_name)
        return result["best"] if result else None

    # ------------------------------------------------------------------
    def shufersal_price(self, item_name: str) -> Optional[Dict[str, str]]:
        """
        Convenience helper: find the price in Shufersal for an item.
        Returns dict with keys: 'store', 'price', 'raw_row' or None.
        """
        result = self.get_prices(item_name)
        return result["shufersal"] if result else None

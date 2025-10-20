"""
supermarket_scraper.py
----------------------
Site-specific scraper for chp.co.il price comparisons.
"""

import re
from typing import Dict, List, Optional, Sequence, Tuple, Union

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
    _LOCATION_HEADER_CANDIDATES = (
        "כתובת",
        "כתובת הסניף",
        "כתובת מלאה",
        "כתובת מדויקת",
        "address",
        "city",
        "עיר",
        "יישוב",
        "ישוב",
        "רחוב",
        "מיקום",
    )
    _BRAND_HEADER_CANDIDATES = (
        "יצרן",
        "שם יצרן",
        "היצרן",
        "מותג",
        "שם המותג",
        "חברה",
        "שם חברה",
        "manufacturer",
        "brand",
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
    def find_barcode(
        self, item_name: str
    ) -> Optional[Tuple[str, Optional[str]]]:
        """
        Look up the product barcode for the given item name.
        Returns:
            Tuple of (barcode, product_name) or None if no match is found.
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

        entry: Union[str, Dict[str, str]] = data[0]
        if isinstance(entry, str):
            return entry, None

        barcode = entry.get("id")
        if not barcode:
            return None

        found_name = (
            entry.get("value")
            or entry.get("label")
            or entry.get("name")
            or entry.get("text")
        )

        raw_parts = entry.get("parts") or {}
        manufacturer_raw = raw_parts.get("manufacturer_and_barcode")
        manufacturer = None
        if isinstance(manufacturer_raw, str):
            manufacturer_clean = manufacturer_raw.strip()
            if manufacturer_clean:
                prefix = "יצרן/מותג:"
                if manufacturer_clean.startswith(prefix):
                    trimmed = manufacturer_clean[len(prefix) :].strip()
                else:
                    trimmed = manufacturer_clean
                for marker in ["ברקוד:", "barcode", "ת.ז.", "barcode:"]:
                    marker_idx = trimmed.find(marker)
                    if marker_idx != -1:
                        trimmed = trimmed[:marker_idx].strip()
                if trimmed:
                    manufacturer = trimmed

        # First result is best match; ID looks like "product_<barcode>"
        return barcode, found_name, manufacturer

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
    def _extract_location(
        self,
        row: Dict[str, str],
        headers: Sequence[str],
        price_columns: Sequence[str],
    ) -> Optional[str]:
        store_header = self._select_store_header(headers)
        for candidate in self._LOCATION_HEADER_CANDIDATES:
            for header in headers:
                if header == store_header:
                    continue
                if candidate.lower() in header.lower():
                    value = row.get(header)
                    if isinstance(value, str) and value.strip():
                        return value.strip()
        for key in row.keys():
            if key in price_columns or key == store_header:
                continue
            value = row.get(key)
            if not isinstance(value, str):
                continue
            normalized = value.strip()
            if not normalized or self._looks_like_price(normalized):
                continue
            return normalized
        return None

    # ------------------------------------------------------------------
    def _extract_brand(
        self,
        row: Dict[str, str],
        headers: Sequence[str],
        price_columns: Sequence[str],
        location_value: Optional[str],
    ) -> Optional[str]:
        values: List[str] = []
        seen = set()
        store_header = self._select_store_header(headers)
        location_headers = {
            header
            for header in headers
            for candidate in self._LOCATION_HEADER_CANDIDATES
            if candidate.lower() in header.lower()
        }
        normalized_location = (
            location_value.strip().lower() if isinstance(location_value, str) else None
        )

        def add_if_valid(raw: Optional[str]) -> None:
            if not isinstance(raw, str):
                return
            cleaned = raw.strip()
            if not cleaned:
                return
            if self._looks_like_price(cleaned):
                return
            lower_cleaned = cleaned.lower()
            if normalized_location and lower_cleaned == normalized_location:
                return
            if any(
                candidate.lower() in lower_cleaned
                for candidate in self._LOCATION_HEADER_CANDIDATES
            ):
                return
            if cleaned not in seen:
                seen.add(cleaned)
                values.append(cleaned)

        for candidate in self._BRAND_HEADER_CANDIDATES:
            for header in headers:
                if candidate.lower() in header.lower():
                    if header in location_headers:
                        continue
                    add_if_valid(row.get(header))

        return " ".join(values) if values else None

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
    ) -> Optional[Dict[str, object]]:
        """
        Fetch all prices for an item and return both best price and Shufersal price.

        Returns:
            Dict with keys:
              * 'best'
              * 'shufersal'
              * 'stores' - list of dicts with keys store/location/price/raw_row
              * 'product_name' - canonical name found on the site (if available)
        """
        lookup = self.find_barcode(item_name)
        if not lookup:
            return None

        barcode, product_name, manufacturer = lookup
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

            location = self._extract_location(row, headers, price_columns)
            brand = self._extract_brand(row, headers, price_columns, location)
            if manufacturer:
                brand = manufacturer if not brand else f"{manufacturer} {brand}"
            price_value = parse_price(price_str)
            if price_value is None:
                continue

            store_entries.append(
                {
                    "store": store_name,
                    "location": location,
                    "brand": brand,
                    "price": price_str,
                    "price_value": price_value,
                    "product_name": product_name,
                    "raw_row": row,
                }
            )

        if not store_entries:
            return None

        store_entries.sort(key=lambda entry: entry["price_value"])
        best_entry = store_entries[0]
        best_price = {
            "store": best_entry["store"],
            "location": best_entry.get("location"),
            "brand": best_entry.get("brand"),
            "product_name": best_entry.get("product_name", product_name),
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
                "location": shufersal_entry.get("location"),
                "brand": shufersal_entry.get("brand"),
                "product_name": shufersal_entry.get(
                    "product_name", product_name
                ),
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
            "product_name": product_name,
        }

    # ------------------------------------------------------------------
    def best_price(self, item_name: str) -> Optional[Dict[str, object]]:
        """
        Convenience helper: find the single best price for an item.
        Returns dict with keys: 'store', 'price', 'raw_row' or None.
        """
        result = self.get_prices(item_name)
        return result["best"] if result else None

    # ------------------------------------------------------------------
    def shufersal_price(self, item_name: str) -> Optional[Dict[str, object]]:
        """
        Convenience helper: find the price in Shufersal for an item.
        Returns dict with keys: 'store', 'price', 'raw_row' or None.
        """
        result = self.get_prices(item_name)
        return result["shufersal"] if result else None

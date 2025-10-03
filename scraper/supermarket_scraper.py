"""
supermarket_scraper.py
----------------------
Site-specific scraper for chp.co.il price comparisons.
"""

from typing import Dict, List, Optional

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper


class SupermarketScraper(BaseScraper):
    """
    Encapsulates all scraping logic for chp.co.il:
    * fetch product barcode by name
    * fetch price comparison table for that barcode
    """

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
    def compare_prices(self, product_barcode: str) -> List[Dict[str, str]]:
        """
        Given a product barcode, fetch the comparison table.

        Returns:
            A list of dicts, each containing the store's columns
            (e.g. {'רשת': 'Store', 'מחיר': '12.90', 'מבצע': ''}).
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

        stores, headers = [], []
        for row in soup.select("table tr"):
            cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
            if not cells:
                continue
            if cells[0] == "רשת":  # header row
                headers = cells
                continue
            if len(cells) == 1:
                continue
            stores.append(dict(zip(headers, cells)))
        return stores

    # ------------------------------------------------------------------
    def _extract_price(self, row: Dict[str, str]) -> str:
        """
        Helper to extract the actual price from a row.
        Prioritizes sale price (מבצע) over regular price (מחיר).
        """
        price = (
            row.get("מבצע").strip("* ").strip() if row.get("מבצע") else row.get("מחיר")
        )
        return price

    # ------------------------------------------------------------------
    def get_prices(
        self, item_name: str
    ) -> Optional[Dict[str, Optional[Dict[str, str]]]]:
        """
        Fetch all prices for an item and return both best price and Shufersal price.

        Returns:
            Dict with keys 'best' and 'shufersal', each containing:
            {'store': str, 'price': str, 'raw_row': dict} or None
        """
        barcode = self.find_barcode(item_name)
        if not barcode:
            return None

        rows = self.compare_prices(barcode)
        if len(rows) < 2:
            return None

        # Best price (first row after headers is cheapest)
        best_store_row = rows[1]
        best_price = {
            "store": best_store_row.get("רשת"),
            "price": self._extract_price(best_store_row),
            "raw_row": best_store_row,
        }

        # Shufersal price
        shfsl_heb = "שופרסל"
        shfsl_row = next(
            (row for row in rows if shfsl_heb in str(row.get("רשת"))), None
        )

        shufersal_price = None
        if shfsl_row:
            shufersal_price = {
                "store": shfsl_row.get("רשת"),
                "price": self._extract_price(shfsl_row),
                "raw_row": shfsl_row,
            }

        return {
            "best": best_price,
            "shufersal": shufersal_price,
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

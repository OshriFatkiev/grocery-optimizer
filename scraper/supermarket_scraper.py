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
        # Base URL isn’t required since we pass absolute URLs,
        # but you can set it if you like: base_url="https://chp.co.il"
        super().__init__()
        self.city_id = city_id
        self.street_id = street_id
        self.city = city
        self.barcode = None

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
    def best_price(self, item_name: str) -> Optional[Dict[str, str]]:
        """
        Convenience helper: find the single best price for an item.
        Returns dict with keys: 'store', 'price', 'raw_row' or None.
        """
        barcode = self.find_barcode(item_name)
        if not barcode:
            return None

        rows = self.compare_prices(barcode)
        if len(rows) < 2:
            return None

        best_store_row = rows[1]  # first row after headers is cheapest
        price = (
            best_store_row.get("מבצע").strip("* ").strip()
            if best_store_row.get("מבצע")
            else best_store_row.get("מחיר")
        )
        return {
            "store": best_store_row.get("רשת"),
            "price": price,
            "raw_row": best_store_row,
        }

    # ------------------------------------------------------------------
    def shufersal_price(self, item_name: str) -> Optional[Dict[str, str]]:
        """
        find the price in Shufersal for an item.
        Returns dict with keys: 'store', 'price', 'raw_row' or None.
        """
        if self.barcode is None:
            barcode = self.find_barcode(item_name)
            if not barcode:
                return None

        rows = self.compare_prices(city)
        if len(rows) < 2:
            return None

        shfsl_heb = "שופרסל"
        shfsl_row = [row for row in rows if shfsl_heb in str(row.get("רשת"))]
        if not shfsl_row:
            return
        shfsl_row = shfsl_row[0]

        price = (
            shfsl_row.get("מבצע").strip("* ").strip()
            if shfsl_row.get("מבצע")
            else shfsl_row.get("מחיר")
        )

        return {
            "store": shfsl_row.get("רשת"),
            "price": price,
            "raw_row": shfsl_row,
        }

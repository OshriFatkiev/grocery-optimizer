"""
price_optimizer.py
------------------
Uses SupermarketScraper to find the cheapest store for each
item in a grocery list and aggregates the results.
"""

import time
from collections import defaultdict
from typing import Dict, List

from tqdm.auto import tqdm

from scraper.supermarket_scraper import SupermarketScraper


class PriceOptimizer:
    """
    High-level interface:
      * read grocery list
      * query prices
      * build dict of store -> list of (item, price)
    """

    def __init__(
        self,
        city: str,
        city_id: int,
        delay: float = 3.0,
        compare_to_shfsl: bool = False,
    ) -> None:
        """
        Args:
            delay: Seconds to sleep between requests to be polite.
        """
        self.scraper = SupermarketScraper(city=city, city_id=city_id)
        self.delay = delay
        self.compare_to_shfsl = compare_to_shfsl

    # ------------------------------------------------------------------
    def run(self, grocery_file: str) -> Dict[str, List[List[str]]]:
        """
        Read items from grocery_file and build price mapping.

        Returns:
            dict[store_name] -> [[item_name, price], ...]
        """
        results: Dict[str, List[List[str]]] = defaultdict(list)

        with open(grocery_file, "r", encoding="utf-8") as f:
            items = [line.strip() for line in f if line.strip()]

        for item in tqdm(items, desc="Processing items", unit="item"):
            time.sleep(self.delay)  # rate-limit requests

            # Fetch all prices at once (single request)
            prices = self.scraper.get_prices(item)
            if not prices:
                continue

            # Add best price
            best = prices["best"]
            if best:
                store, price = best["store"], best["price"]
                results[store].append([item, price])

            # Add Shufersal price if requested
            if self.compare_to_shfsl:
                shfsl = prices["shufersal"]
                if shfsl:
                    store, price = shfsl["store"], shfsl["price"]
                    results[store].append([item, price])

        return results

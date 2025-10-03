"""
price_optimizer.py
------------------
Uses SupermarketScraper to find the cheapest store for each
item in a grocery list and aggregates the results.
"""

import time
from collections import defaultdict
from typing import Dict, List

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

        total = len(items)
        for idx, item in enumerate(items, start=1):  # tqdm(items):
            time.sleep(self.delay)  # rate-limit requests
            print(f"[{idx}/{total}]: {item}")
            best = self.scraper.best_price(item)
            if not best:
                print(f"  No price data found for '{item}'")
                continue
            store, price = best["store"], best["price"]
            results[store].append([item, price])
            print(f"  -> {store}: {price}")

            time.sleep(self.delay)  # rate-limit requests

            # add Shufersal price if self.compare_to_shfsl is True
            if self.compare_to_shfsl:
                shfsl = self.scraper.shufersal_price(item)
                if not shfsl:
                    print(f"  No Shufersal data found for '{item}'")
                    continue
                store, price = shfsl["store"], shfsl["price"]
                results[store].append([item, price])
                print(f"  -> {store}: {price}")

            time.sleep(self.delay)  # rate-limit requests

        return results

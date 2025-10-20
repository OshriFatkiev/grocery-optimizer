"""
price_optimizer.py
------------------
Uses SupermarketScraper to find the cheapest combination of stores
for a grocery list, optionally limiting the number of stores.
"""

import logging
import math
import time
from collections import defaultdict
from itertools import combinations
from typing import Dict, List, NamedTuple, Optional, Sequence, Tuple

from tqdm.auto import tqdm

from scraper.supermarket_scraper import SupermarketScraper
from utils.parser import parse_price


class StoreOption(NamedTuple):
    name: str
    location: Optional[str]
    price_value: float
    price_str: str


ItemOptions = Tuple[str, Sequence[StoreOption]]
AssignmentEntry = Tuple[str, str, float]
AssignmentMap = Dict[str, List[AssignmentEntry]]


class PriceOptimizer:
    """
    High-level interface:
      * read grocery list
      * query prices
      * build dict of store -> list of (item, price)
      * optionally restrict to visiting at most N stores
    """

    def __init__(
        self,
        city: str,
        city_id: int,
        delay: float = 3.0,
        compare_to_shfsl: bool = False,
        max_stores: Optional[int] = None,
    ) -> None:
        """
        Args:
            delay: Seconds to sleep between requests to be polite.
            max_stores: Limit the optimizer to at most this many stores.
        """
        self.scraper = SupermarketScraper(city=city, city_id=city_id)
        self.delay = delay
        self.compare_to_shfsl = compare_to_shfsl
        self.max_stores = max_stores
        self.last_total_cost: Optional[float] = None

    # ------------------------------------------------------------------
    def run(self, grocery_file: str) -> Dict[str, List[List[str]]]:
        """
        Read items from grocery_file and build price mapping.

        Returns:
            dict[store_name] -> [[item_name, price], ...]
        """
        items = self._read_items(grocery_file)
        if not items:
            logging.warning("No items found in %s.", grocery_file)
            return {}

        item_options, missing_items = self._collect_prices(items)
        if missing_items:
            unique_missing = sorted(set(missing_items))
            logging.warning(
                "No prices found for %d item(s): %s",
                len(unique_missing),
                ", ".join(unique_missing),
            )

        if not item_options:
            logging.warning("No price data available for the requested items.")
            return {}

        assignments, total_cost = self._assign_items(item_options)
        self.last_total_cost = total_cost

        if total_cost is not None:
            logging.debug(
                "Selected stores %s with total cost %.2f",
                list(assignments.keys()),
                total_cost,
            )

        results = self._format_results(assignments)

        if self.compare_to_shfsl:
            shufersal_entry = self._build_shufersal_comparison(item_options, results)
            if shufersal_entry:
                store_name, entries = shufersal_entry
                results[store_name] = entries

        return results

    # ------------------------------------------------------------------
    def _read_items(self, grocery_file: str) -> List[str]:
        with open(grocery_file, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]

    # ------------------------------------------------------------------
    def _collect_prices(
        self, items: Sequence[str]
    ) -> Tuple[List[ItemOptions], List[str]]:
        price_cache: Dict[str, Tuple[StoreOption, ...]] = {}
        item_options: List[ItemOptions] = []
        missing_items: List[str] = []

        for item in tqdm(items, desc="Processing items", unit="item"):
            store_prices = price_cache.get(item)
            if store_prices is None:
                time.sleep(self.delay)
                store_prices = self._fetch_store_prices(item)
                price_cache[item] = store_prices

            if not store_prices:
                missing_items.append(item)
                continue

            item_options.append((item, store_prices))

        return item_options, missing_items

    # ------------------------------------------------------------------
    def _fetch_store_prices(self, item: str) -> Tuple[StoreOption, ...]:
        prices = self.scraper.get_prices(item)
        if not prices:
            return ()

        store_entries: List[StoreOption] = []
        for entry in prices.get("stores", []):
            store = entry.get("store")
            location = entry.get("location")
            price_str = entry.get("price")
            price_value = entry.get("price_value")
            if not store or not price_str:
                continue
            if price_value is None:
                price_value = parse_price(price_str)
            if price_value is None:
                continue
            store_entries.append(StoreOption(store, location, price_value, price_str))

        store_entries.sort(key=lambda value: value.price_value)
        return tuple(store_entries)

    # ------------------------------------------------------------------
    def _store_label(self, store_name: str, location: Optional[str]) -> str:
        label = store_name.strip()
        if location:
            loc = location.strip()
            if loc and loc not in label:
                label = f"{label} - {loc}"
        return label

    # ------------------------------------------------------------------
    def _assign_items(
        self, item_options: Sequence[ItemOptions]
    ) -> Tuple[AssignmentMap, Optional[float]]:
        if not item_options:
            return {}, 0.0

        if self.max_stores is None:
            return self._assign_unlimited(item_options)

        assignments, total_cost = self._find_best_combination(item_options, self.max_stores)
        if assignments is None or total_cost is None:
            logging.warning(
                "Unable to satisfy store limit %s. Falling back to best-per-item assignment.",
                self.max_stores,
            )
            return self._assign_unlimited(item_options)

        return assignments, total_cost

    # ------------------------------------------------------------------
    def _assign_unlimited(
        self, item_options: Sequence[ItemOptions]
    ) -> Tuple[AssignmentMap, float]:
        assignments: AssignmentMap = defaultdict(list)
        total_cost = 0.0

        for item_name, store_prices in item_options:
            if not store_prices:
                continue
            best_option = min(store_prices, key=lambda entry: entry.price_value)
            store_label = self._store_label(best_option.name, best_option.location)
            assignments[store_label].append(
                (item_name, best_option.price_str, best_option.price_value)
            )
            total_cost += best_option.price_value

        return assignments, total_cost

    # ------------------------------------------------------------------
    def _find_best_combination(
        self, item_options: Sequence[ItemOptions], max_stores: int
    ) -> Tuple[Optional[AssignmentMap], Optional[float]]:
        store_labels = sorted(
            {
                self._store_label(option.name, option.location)
                for _, store_prices in item_options
                for option in store_prices
            }
        )
        if not store_labels:
            return None, None

        max_size = min(max_stores, len(store_labels))
        if max_size >= len(store_labels):
            return self._assign_unlimited(item_options)

        combination_count = sum(
            math.comb(len(store_labels), r) for r in range(1, max_size + 1)
        )
        if combination_count > 100_000:
            logging.warning(
                "Store limit %s creates %d combinations; using greedy assignment instead.",
                max_stores,
                combination_count,
            )
            return self._assign_unlimited(item_options)

        best_assignment: Optional[AssignmentMap] = None
        best_total = float("inf")

        for size in range(1, max_size + 1):
            for combo in combinations(store_labels, size):
                combo_set = set(combo)
                assignment: AssignmentMap = defaultdict(list)
                total_cost = 0.0
                feasible = True

                for item_name, store_prices in item_options:
                    best_option: Optional[StoreOption] = None
                    best_label: Optional[str] = None
                    for option in store_prices:
                        label = self._store_label(option.name, option.location)
                        if label not in combo_set:
                            continue
                        if (
                            best_option is None
                            or option.price_value < best_option.price_value
                        ):
                            best_option = option
                            best_label = label

                    if best_option is None or best_label is None:
                        feasible = False
                        break

                    assignment[best_label].append(
                        (
                            item_name,
                            best_option.price_str,
                            best_option.price_value,
                        )
                    )
                    total_cost += best_option.price_value

                    if total_cost >= best_total:
                        feasible = False
                        break

                if not feasible:
                    continue

                if total_cost < best_total:
                    best_total = total_cost
                    best_assignment = assignment

        if best_assignment is None:
            return None, None

        return best_assignment, best_total

    # ------------------------------------------------------------------
    def _format_results(self, assignments: AssignmentMap) -> Dict[str, List[List[str]]]:
        if not assignments:
            return {}

        store_totals = {
            store: sum(price for _, _, price in entries)
            for store, entries in assignments.items()
        }
        ordered_stores = sorted(assignments.keys(), key=lambda store: store_totals[store])

        formatted: Dict[str, List[List[str]]] = {}
        for store in ordered_stores:
            formatted[store] = [
                [item_name, price_str] for item_name, price_str, _ in assignments[store]
            ]

        return formatted

    # ------------------------------------------------------------------
    def _build_shufersal_comparison(
        self,
        item_options: Sequence[ItemOptions],
        existing_results: Dict[str, List[List[str]]],
    ) -> Optional[Tuple[str, List[List[str]]]]:
        marker = getattr(self.scraper, "SHUFERSAL_LABEL", None)
        if not marker:
            return None

        store_name: Optional[str] = None
        entries: List[List[str]] = []

        for item_name, store_prices in item_options:
            match = next(
                (entry for entry in store_prices if marker in entry.name), None
            )
            if not match:
                continue
            store_name = self._store_label(match.name, match.location)
            entries.append([item_name, match.price_str])

        if store_name and entries and store_name not in existing_results:
            return store_name, entries

        return None

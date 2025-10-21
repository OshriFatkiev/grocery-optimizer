#!/usr/bin/env python3
"""
main.py
-------
Entry point for grocery_optimizer.
Example:
    python main.py --formats yaml csv --input input/groceries.txt --notify
"""

import argparse
import logging

from optimizer.price_optimizer import PriceOptimizer
from utils.convert_bycode import get_city_from_json
from utils.exporter import export_csv, export_txt, export_yaml
from utils.notifier import send_telegram_message


def _positive_int(value: str) -> int:
    ivalue = int(value)
    if ivalue <= 0:
        raise argparse.ArgumentTypeError(
            f"Invalid value '{value}'. Number of stores must be positive."
        )
    return ivalue


def parse_args():
    parser = argparse.ArgumentParser(
        description="Find cheapest supermarkets for a grocery list."
    )
    parser.add_argument(
        "-i",
        "--input",
        default="input/groceries.txt",
        help="Path to input grocery list (default: input/groceries.txt)",
    )
    parser.add_argument(
        "-f",
        "--formats",
        nargs="+",
        choices=["yaml", "csv", "txt"],
        default=["yaml"],
        help="Output formats to save (choose one or more: yaml csv txt). Default: yaml",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=3.0,
        help="Seconds to wait between requests (default: 3.0)",
    )
    parser.add_argument(
        "--notify",
        action="store_true",
        help="Send results to Telegram if BOT_TOKEN/CHAT_ID are set.",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable debug logging."
    )

    parser.add_argument(
        "--compare-to-shfsl",
        action="store_true",
        help="Create also a Shufersal list for comparison.",
    )

    parser.add_argument(
        "--city",
        type=str,
        default="מעלה אדומים",
        help="City name to use for store price optimization.",
    )

    parser.add_argument(
        "--max-stores",
        type=_positive_int,
        default=None,
        help="Limit the optimizer to at most this many stores.",
    )
    parser.add_argument(
        "--use-found-names",
        action="store_true",
        help="Replace item names with the product names returned by the site.",
    )
    parser.add_argument(
        "--add-brand",
        action="store_true",
        default=True,
        help="Append manufacturer/brand information to item names when available.",
    )
    parser.add_argument(
        "--add-store-location",
        action="store_true",
        help="Append store locations to store names when available.",
    )

    return parser.parse_args()


logger = logging.getLogger(__name__)


def main():
    args = parse_args()

    # Configure the logging system
    LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format=LOG_FORMAT,
    )

    # Check input.txt
    # is_hebrew = all_words_hebrew(args.input)
    # if not is_hebrew:
    #     return

    city_eng, city_id = get_city_from_json(args.city)
    if not city_id:
        logger.error(f"City '{args.city}' not found in cities.json")
        return
    logger.info(f"Using city: {city_eng} (ID: {city_id})")

    optimizer = PriceOptimizer(
        delay=args.delay,
        city=args.city,
        city_id=city_id,
        compare_to_shfsl=args.compare_to_shfsl,
        max_stores=args.max_stores,
        use_found_names=args.use_found_names,
        add_brand=args.add_brand,
        add_store_location=args.add_store_location,
    )
    results = optimizer.run(args.input)
    logger.debug(f"Results: {results}")

    # Export to selected formats with default filenames
    if args.formats:
        for fmt in args.formats:
            if fmt == "yaml":
                export_yaml(results)
            elif fmt == "csv":
                export_csv(results)
            elif fmt == "txt":
                export_txt(results)

    if args.notify:
        send_telegram_message(results, args.compare_to_shfsl)


if __name__ == "__main__":
    main()

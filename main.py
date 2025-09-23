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
from utils.exporter import export_yaml, export_csv, export_txt
from utils.notifier import send_telegram_message


def parse_args():
    parser = argparse.ArgumentParser(
        description="Find cheapest supermarkets for a grocery list."
    )
    parser.add_argument(
        "-i", "--input",
        default="input/groceries.txt",
        help="Path to input grocery list (default: input/groceries.txt)"
    )
    parser.add_argument(
        "-f", "--formats",
        nargs="+",
        choices=["yaml", "csv", "txt"],
        default=["yaml"],
        help="Output formats to save (choose one or more: yaml csv txt). Default: yaml"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=3.0,
        help="Seconds to wait between requests (default: 3.0)"
    )
    parser.add_argument(
        "--notify",
        action="store_true",
        help="Send results to Telegram if BOT_TOKEN/CHAT_ID are set."
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug logging."
    )
    return parser.parse_args()


def main():
    args = parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)

    optimizer = PriceOptimizer(delay=args.delay)
    results = optimizer.run(args.input)

    # Export to selected formats with default filenames
    for fmt in args.formats:
        if fmt == "yaml":
            export_yaml(results)
        elif fmt == "csv":
            export_csv(results)
        elif fmt == "txt":
            export_txt(results)

    if args.notify:
        send_telegram_message(results)


if __name__ == "__main__":
    main()

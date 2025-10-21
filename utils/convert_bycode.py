#!/usr/bin/env python3
"""
Convert CBS 'bycode2023.xlsx' (locality codes) into JSON.
Link to download: https://www.cbs.gov.il/he/publications/doclib/2019/ishuvim/bycode2023.xlsx

Usage:
    python convert_bycode.py -i bycode2023.xlsx -o cities.json
"""

import argparse
import json
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def get_city_from_json(city_name, filepath="cities.json"):
    path = Path(filepath)

    # Check if file exists
    if not path.exists():
        raise FileNotFoundError(f"Cities file not found: {path.resolve()}")

    # Load JSON from file
    with open(path, encoding="utf-8") as f:
        cities = json.load(f)

    # Search for the city
    for city in cities:
        if city["heb_name"] == city_name:
            return city["eng_name"], city["code"]

    return (None, None)  # If not found


def parse_args():
    """Set up and return parsed command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Convert CBS bycode Excel file to JSON format."
    )
    parser.add_argument(
        "-i",
        "--input",
        default="bycode2023.xlsx",
        help="Path to the input Excel file",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="cities.json",
        help="Path to the output JSON file",
    )
    return parser.parse_args()


def convert_excel_to_json(input_path, output_path):
    """Read CBS Excel file and write it as JSON."""
    df = pd.read_excel(input_path)

    # Keep only relevant columns
    df = df[["סמל יישוב", "שם יישוב באנגלית", "שם יישוב"]]

    # Rename for easier programmatic use
    df = df.rename(
        columns={
            "סמל יישוב": "code",
            "שם יישוב": "heb_name",
            "שם יישוב באנגלית": "eng_name",
        }
    )

    # Write to JSON
    df.to_json(output_path, orient="records", force_ascii=False, indent=2)

    logger.info(f"Saved {len(df)} records to {output_path}")


def main():
    args = parse_args()
    logging.basicConfig(level=logging.INFO)
    convert_excel_to_json(args.input, args.output)


if __name__ == "__main__":
    main()

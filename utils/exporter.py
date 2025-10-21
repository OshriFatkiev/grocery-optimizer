# grocery_optimizer/utils/exporter.py

import csv
import logging
from datetime import datetime
from typing import Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M")


def export_yaml(data: Dict[str, List[List[str]]], path: Optional[str] = None) -> str:
    """Save results to YAML. Returns the file path used."""
    if not path:
        path = f"output/grocery_list_{_timestamp()}.yaml"
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(dict(data), f, allow_unicode=True, default_flow_style=False)
    logger.info(f"Saved YAML to {path}")
    return path


def export_txt(data: Dict[str, List[List[str]]], path: Optional[str] = None) -> str:
    """Save results to plain text."""
    if not path:
        path = f"output/grocery_list_{_timestamp()}.txt"
    with open(path, "w", encoding="utf-8") as f:
        for store, items in data.items():
            f.write(f"{store}:\n")
            for item, price in items:
                f.write(f"- {item}: {price}\n")
            f.write("\n")
    logger.info(f"Saved TXT to {path}")
    return path


def export_csv(data: Dict[str, List[List[str]]], path: Optional[str] = None) -> str:
    """Save results to CSV."""
    if not path:
        path = f"output/grocery_list_{_timestamp()}.csv"
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["store", "item", "price"])
        for store, items in data.items():
            for item, price in items:
                writer.writerow([store, item, price])
    logger.info(f"Saved CSV to {path}")
    return path

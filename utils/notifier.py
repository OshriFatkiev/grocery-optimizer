"""
notifier.py
-----------
Send grocery summary messages via Telegram bot.
"""

import logging
import os
from typing import Dict, List

import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()


def send_telegram_message(
    data: Dict[str, List[List[str]]],
    compare_to_shfsl: bool = False,
    compact: bool = False,
    attach_full: bool = False,
) -> bool:
    """
    Send a nicely formatted grocery list to a Telegram chat.

    Args:
        data: Dict of store -> [[item, price], ...]
        compare_to_shfsl: If True, include Shufersal column

    Returns:
        True if the message was sent successfully.
    """
    bot_token = os.getenv("BOT_TOKEN")
    chat_id = os.getenv("CHAT_ID")

    if not bot_token or not chat_id:
        logger.warning("Telegram credentials missing. Check your .env file.")
        return False

    # Choose formatter based on compact mode
    message_text = (
        _format_compact_message(data, compare_to_shfsl)
        if compact
        else _format_price_table(data, compare_to_shfsl)
    )

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    # Build message parts within Telegram limits (4096 chars)
    parts = _chunk_message(message_text, limit=4096)
    success = True
    for idx, part in enumerate(parts, start=1):
        payload = {
            "chat_id": chat_id,
            "text": part,
            "parse_mode": "HTML",
        }
        if compact:
            payload["disable_web_page_preview"] = True

        try:
            resp = requests.post(url, data=payload, timeout=10)
            if resp.ok:
                logger.info(
                    "Telegram message part %d/%d sent successfully.", idx, len(parts)
                )
            else:
                logger.error("Error sending Telegram message: %s", resp.text)
                success = False
        except requests.RequestException as e:
            logger.error(f"Telegram request failed: {e}")
            success = False

    # Optionally attach full table as a text file when using compact mode
    if compact and attach_full:
        try:
            full_table = _format_price_table(data, compare_to_shfsl)
            url_doc = f"https://api.telegram.org/bot{bot_token}/sendDocument"
            files = {
                "document": (
                    "grocery_report.txt",
                    full_table.encode("utf-8"),
                    "text/plain",
                )
            }
            data_doc = {"chat_id": chat_id, "caption": "Full price table"}
            resp = requests.post(url_doc, data=data_doc, files=files, timeout=15)
            if resp.ok:
                logger.info("Attached full table as a document.")
            else:
                logger.error("Failed to attach document: %s", resp.text)
                success = False
        except requests.RequestException as e:
            logger.error(f"Telegram document upload failed: {e}")
            success = False

    return success


def _format_price_table(
    data: Dict[str, List[List[str]]], compare_to_shfsl: bool
) -> str:
    """
    Format as a right-aligned table.

    Args:
        data: Dict of store -> [[item, price], ...]
        compare_to_shfsl: If True, include Shufersal column
    """
    item_prices = {}

    # 1. Aggregate data (same as before)
    for store, items in data.items():
        is_shfsl = "שופרסל" in store
        for item, price in items:
            if item not in item_prices:
                item_prices[item] = {
                    "best_store": store,
                    "best_price": price,
                    "shfsl_price": None,
                }
            else:
                if item_prices[item]["best_price"] is None or float(price) < float(
                    item_prices[item]["best_price"]
                ):
                    item_prices[item]["best_price"] = price
                    item_prices[item]["best_store"] = store
            if is_shfsl:
                item_prices[item]["shfsl_price"] = price

    # 2. NEW: Sanitize all data *before* calculating widths
    # This removes hidden characters that break alignment.
    cleaned_prices = {}
    for item, details in item_prices.items():
        cleaned_prices[item.strip()] = {
            "best_store": (details["best_store"] or "").strip(),
            "best_price": (details["best_price"] or "").strip(),
            "shfsl_price": (details["shfsl_price"] or "").strip(),
        }

    # If there's no data after cleaning, return early.
    if not cleaned_prices:
        return "<pre>No items to display.</pre>"

    # 3. Calculate widths using the now-cleaned data
    item_header = "פריט"
    store_header = "חנות"
    price_header = "מחיר"
    shfsl_header = "שופרסל"
    padding = 2

    max_item_len = max((len(item) for item in cleaned_prices.keys()), default=0)
    item_width = max(max_item_len, len(item_header)) + padding

    max_store_len = max(
        (len(p["best_store"] or "") for p in cleaned_prices.values()), default=0
    )
    store_width = max(max_store_len, len(store_header)) + padding

    max_best_price_len = max(
        (len(p["best_price"] or "") for p in cleaned_prices.values()), default=0
    )
    price_width = max(max_best_price_len, len(price_header)) + padding

    # 4. Build the table
    lines = ["<pre>"]
    header_parts = [
        item_header.ljust(item_width),
        store_header.ljust(store_width),
        price_header.ljust(price_width),
    ]

    if compare_to_shfsl:
        max_shfsl_len = max(
            (len(p["shfsl_price"] or "") for p in cleaned_prices.values()), default=0
        )
        shfsl_width = max(max_shfsl_len, len(shfsl_header)) + padding
        header_parts.append(shfsl_header.ljust(shfsl_width))

    lines.append("".join(header_parts))
    lines.append("─" * sum(len(p) for p in header_parts))

    # Rows (using cleaned data)
    for item, prices in cleaned_prices.items():
        best_store = prices["best_store"] or "N/A"
        best_price = prices["best_price"] or "N/A"

        row_parts = [
            item.ljust(item_width),
            best_store.ljust(store_width),
            str(best_price).ljust(price_width),
        ]
        if compare_to_shfsl:
            shfsl_price = prices["shfsl_price"] or "N/A"
            row_parts.append(str(shfsl_price).ljust(shfsl_width))

        lines.append("".join(row_parts))

    # 5. Add a non-breaking space as a "bumper" before the closing tag
    # This prevents Telegram client rendering glitches on the last line.
    lines.append("\u200b")  # Using a zero-width space

    lines.append("</pre>")
    return "\n".join(lines)


def _chunk_message(text: str, limit: int = 4096) -> List[str]:
    """Split text into parts not exceeding Telegram's message size limit."""
    if len(text) <= limit:
        return [text]

    parts: List[str] = []
    current: List[str] = []
    current_len = 0
    for line in text.splitlines():
        # Ensure each line ends with a newline for readability
        to_add = line + "\n"
        if current_len + len(to_add) > limit:
            parts.append("".join(current).rstrip("\n"))
            current = [to_add]
            current_len = len(to_add)
        else:
            current.append(to_add)
            current_len += len(to_add)
    if current:
        parts.append("".join(current).rstrip("\n"))
    return parts


def _insert_zwsp(s: str) -> str:
    """Insert zero-width spaces to allow wrapping on mobile UIs."""
    return (
        s.replace("/", "/\u200b")
        .replace("-", "-\u200b")
        .replace("_", "_\u200b")
        .replace(".", ".\u200b")
    )


def _truncate(s: str, max_len: int = 32) -> str:
    if len(s) <= max_len:
        return s
    return s[: max_len - 1] + "…"


def _format_compact_message(
    data: Dict[str, List[List[str]]], compare_to_shfsl: bool
) -> str:
    """
    Mobile-friendly compact list layout without <pre> blocks.
    Each line: • <b>Item</b> Store Price (Shufersal Price)
    """
    # Aggregate best prices similarly to the table formatter
    item_prices = {}
    for store, items in data.items():
        is_shfsl = "שופרסל" in store
        for item, price in items:
            if item not in item_prices:
                item_prices[item] = {
                    "best_store": store,
                    "best_price": price,
                    "shfsl_price": None,
                }
            else:
                if item_prices[item]["best_price"] is None or float(price) < float(
                    item_prices[item]["best_price"]
                ):
                    item_prices[item]["best_price"] = price
                    item_prices[item]["best_store"] = store
            if is_shfsl:
                item_prices[item]["shfsl_price"] = price

    lines: List[str] = []
    # Optional simple header
    # lines.append("<b>Optimized Grocery List</b>")

    total = len(item_prices)
    for i, (item, details) in enumerate(item_prices.items()):
        item_txt = _truncate(_insert_zwsp((item or "").strip()), 36)
        store_txt = _truncate(
            _insert_zwsp((details.get("best_store") or "N/A").strip()), 30
        )
        best_price = (details.get("best_price") or "N/A").strip()
        shfsl_price = details.get("shfsl_price") or None

        lines.append(f"• <b>{item_txt}</b>")
        lines.append(f"  {store_txt} {best_price}")
        if compare_to_shfsl and shfsl_price:
            lines.append(f"  שופרסל {shfsl_price}")
        if i < total - 1:
            lines.append("")

    # Prevent rendering glitches on the last line
    lines.append("\u200b")
    return "\n".join(lines)


if __name__ == "__main__":
    from collections import defaultdict

    logging.basicConfig(level=logging.INFO)

    # Example usage
    data = defaultdict(list)
    data.update(
        {
            "מעיין 2000": [["תפוח אדמה אדום", "3.90"], ["שישיית עין גדי", "10.00"]],
            "שופרסל דיל": [
                ["תפוח אדמה אדום", "4.90"],
                ["בטטה", "9.90"],
                ["שישיית עין גדי", "16.90"],
                ["סלרי", "7.90"],
                ["סלרי", "7.90"],
            ],
            "רמי לוי": [["בטטה", "2.80"]],
        },
    )
    send_telegram_message(data, compare_to_shfsl=True)

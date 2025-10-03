"""
notifier.py
-----------
Send grocery summary messages via Telegram bot.
"""

import os
from typing import Dict, List

import requests
from dotenv import load_dotenv

load_dotenv()


def send_telegram_message(
    data: Dict[str, List[List[str]]], compare_to_shfsl: bool = False
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
        print("Telegram credentials missing. Check your .env file.")
        return False

    message_text = _format_price_table(data, compare_to_shfsl)

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message_text, "parse_mode": "HTML"}

    try:
        resp = requests.post(url, data=payload, timeout=10)
        if resp.ok:
            print("Telegram message sent successfully.")
            return True
        else:
            print("Error sending Telegram message:", resp.text)
            return False
    except requests.RequestException as e:
        print("Telegram request failed:", e)
        return False


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


if __name__ == "__main__":
    from collections import defaultdict

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

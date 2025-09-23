"""
notifier.py
-----------
Send grocery summary messages via Telegram bot.
"""

import os
import requests
from dotenv import load_dotenv
from typing import Dict, List

load_dotenv()


def send_telegram_message(data: Dict[str, List[List[str]]]) -> bool:
    """
    Send a nicely formatted grocery list to a Telegram chat.

    Args:
        data: Dict of store -> [[item, price], ...]

    Returns:
        True if the message was sent successfully.
    """
    bot_token = os.getenv("BOT_TOKEN")
    chat_id = os.getenv("CHAT_ID")

    if not bot_token or not chat_id:
        print("Telegram credentials missing. Check your .env file.")
        return False

    RTL = "\u200F"  # Right-to-left marker for Hebrew
    lines = []
    for store, items in data.items():
        lines.append(f"{RTL}{store}:")
        for item, price in items:
            lines.append(f"{RTL}- {item} ({price})")
    message_text = "\n".join(lines)

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message_text}

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

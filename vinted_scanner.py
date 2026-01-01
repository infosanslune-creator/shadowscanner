#!/usr/bin/env python3
import os
import sys
import json
import time
import copy
import logging
import requests
import smtplib
import email.utils
from email.message import EmailMessage
from logging.handlers import RotatingFileHandler

import Config

# =========================
# Logging
# =========================
handler = RotatingFileHandler(
    "vinted_scanner.log",
    maxBytes=5_000_000,
    backupCount=5
)

logging.basicConfig(
    handlers=[handler],
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# =========================
# Globals
# =========================
timeoutconnection = 30
list_analyzed_items = []

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "nl-NL,nl;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.vinted.nl/",
    "Origin": "https://www.vinted.nl",
    "Connection": "keep-alive",
}

# =========================
# Helpers
# =========================
def safe_get_json(response):
    if response.status_code != 200:
        logging.error(f"HTTP {response.status_code} from Vinted")
        logging.debug(response.text[:300])
        return None
    try:
        return response.json()
    except ValueError:
        logging.error("Invalid JSON from Vinted")
        logging.debug(response.text[:300])
        return None


def load_analyzed_items():
    if not os.path.exists("vinted_items.txt"):
        return
    with open("vinted_items.txt", "r", errors="ignore") as f:
        for line in f:
            if line.strip():
                list_analyzed_items.append(line.strip())


def save_analyzed_item(item_id):
    with open("vinted_items.txt", "a") as f:
        f.write(f"{item_id}\n")


# =========================
# Notifications
# =========================
def send_telegram_message(title, price, url, image):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", Config.telegram_bot_token)
    chat_id = os.getenv("TELEGRAM_CHAT_ID", Config.telegram_chat_id)

    if not bot_token or not chat_id:
        logging.error("Telegram credentials missing")
        return

    message = (
        f"<b>{title}</b>\n"
        f"Prijs: {price}\n"
        f"{url}\n"
        f"{image}"
    )

    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    try:
        r = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json=payload,
            timeout=timeoutconnection
        )
        logging.info(f"Telegram HTTP {r.status_code}")
    except Exception as e:
        logging.error(f"Telegram error: {e}", exc_info=True)


# =========================
# Main
# =========================
def main():
    logging.info("Scanner run started")
    load_analyzed_items()

    session = requests.Session()

    try:
        session.post(Config.vinted_url, headers=headers, timeout=timeoutconnection)
    except Exception as e:
        logging.error(f"Session init failed: {e}")
        return

    cookies = session.cookies.get_dict()

    for base_params in Config.queries:
        max_pages = int(base_params.get("max_pages", 1))

        params = copy.deepcopy(base_params)
        params.pop("max_pages", None)

        for page in range(1, max_pages + 1):
            params["page"] = str(page)
            params["_"] = int(time.time())  # cache-bypass

            logging.info(f"Fetching page {page}")

            try:
                response = requests.get(
                    f"{Config.vinted_url}/api/v2/catalog/items",
                    params=params,
                    cookies=cookies,
                    headers=headers,
                    timeout=timeoutconnection,
                )
            except Exception as e:
                logging.error(f"Request failed: {e}")
                continue

            data = safe_get_json(response)
            if not data:
                continue

            items = data.get("items", [])
            logging.info(f"Vinted returned {len(items)} items on page {page}")

            for item in items:
                item_id = str(item.get("id"))
                if not item_id:
                    continue

                if item_id in list_analyzed_items:
                    logging.info(f"Skipping known item {item_id}")
                    continue

                title = item.get("title", "Unknown")
                url = item.get("url", "")
                price_data = item.get("price", {})
                price = f"{price_data.get('amount', '?')} {price_data.get('currency_code', '')}"
                image = item.get("photo", {}).get("full_size_url", "")

                logging.info(f"NEW ITEM: {title} | {price}")

                send_telegram_message(title, price, url, image)

                list_analyzed_items.append(item_id)
                save_analyzed_item(item_id)

    logging.info("Scanner run finished")


if __name__ == "__main__":
    main()

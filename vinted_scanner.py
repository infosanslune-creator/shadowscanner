#!/usr/bin/env python3
import os
import json
import time
import copy
import logging
import requests
from logging.handlers import RotatingFileHandler

import Config
import google.generativeai as genai

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
# Gemini setup
# =========================
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
gemini_model = genai.GenerativeModel("gemini-1.5-flash")

# =========================
# Helpers
# =========================
def safe_get_json(response):
    if response.status_code != 200:
        logging.error(f"HTTP {response.status_code} from Vinted")
        return None
    try:
        return response.json()
    except ValueError:
        logging.error("Invalid JSON from Vinted")
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
# Gemini price evaluation
# =========================
def evaluate_gpu_price(title, price_eur):
    prompt = f"""
Je bent een expert in tweedehands GPU prijzen in Europa (2024–2026).

Geef ALLEEN JSON:

{{
  "label": "No brainer | Goede prijs | Slechte prijs | Onzeker",
  "market_value": "€X–€Y of onbekend"
}}

Titel: "{title}"
Prijs: {price_eur} EUR
"""

    try:
        response = gemini_model.generate_content(prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        logging.error(f"Gemini error: {e}")
        return {
            "label": "Onzeker",
            "market_value": "onbekend"
        }


# =========================
# Telegram
# =========================
def send_telegram_message(title, price, analysis, url, image):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        logging.error("Telegram credentials missing")
        return

    message = (
        f"<b>{title}</b>\n\n"
        f"🧠 {analysis['label']} (marktwaarde {analysis['market_value']})\n"
        f"💰 Prijs: {price}\n\n"
        f"🔗 <a href=\"{url}\">Bekijk op Vinted</a>\n"
        f"{image}"
    )

    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,  # 👈 image preview AAN
    }

    try:
        requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json=payload,
            timeout=timeoutconnection
        )
        logging.info("Telegram message sent")
    except Exception as e:
        logging.error(f"Telegram error: {e}", exc_info=True)


# =========================
# Main
# =========================
def main():
    logging.info("Scanner run started")
    load_analyzed_items()

    session = requests.Session()
    session.post(Config.vinted_url, headers=headers, timeout=timeoutconnection)
    cookies = session.cookies.get_dict()

    for base_params in Config.queries:
        max_pages = int(base_params.get("max_pages", 1))
        params = copy.deepcopy(base_params)
        params.pop("max_pages", None)

        for page in range(1, max_pages + 1):
            params["page"] = str(page)
            params["_"] = int(time.time())  # cache-bypass

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

            for item in data.get("items", []):
                item_id = str(item.get("id"))
                if not item_id or item_id in list_analyzed_items:
                    continue

                title = item.get("title", "Unknown")
                url = item.get("url", "")
                price_data = item.get("price", {})
                price_value = float(price_data.get("amount", 0))
                price = f"{price_value} {price_data.get('currency_code', '')}"
                image = item.get("photo", {}).get("full_size_url", "")

                analysis = evaluate_gpu_price(title, price_value)

                send_telegram_message(
                    title=title,
                    price=price,
                    analysis=analysis,
                    url=url,
                    image=image
                )

                list_analyzed_items.append(item_id)
                save_analyzed_item(item_id)

    logging.info("Scanner run finished")


if __name__ == "__main__":
    main()

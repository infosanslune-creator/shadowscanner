#!/usr/bin/env python3
import sys
import json
import os
import Config
import smtplib
import logging
import requests
import email.utils
from email.message import EmailMessage
from logging.handlers import RotatingFileHandler

# =========================
# Logging
# =========================
handler = RotatingFileHandler("vinted_scanner.log", maxBytes=5_000_000, backupCount=5)

logging.basicConfig(
    handlers=[handler],
    format="%(asctime)s - %(filename)s - %(funcName)10s():%(lineno)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# =========================
# Globals
# =========================
timeoutconnection = 30
list_analyzed_items = []

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
    "Accept-Language": "nl-NL,nl;q=0.8,en-US;q=0.5,en;q=0.3",
    "DNT": "1",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
}

# =========================
# Helpers
# =========================
def safe_get_json(response):
    """Safely parse JSON, return None on failure."""
    if response.status_code != 200:
        logging.error(f"HTTP {response.status_code} from Vinted API")
        logging.debug(response.text[:500])
        return None

    try:
        return response.json()
    except ValueError:
        logging.error("Invalid JSON returned by Vinted API")
        logging.debug(response.text[:500])
        return None


def load_analyzed_item():
    try:
        with open("vinted_items.txt", "r", errors="ignore") as f:
            for line in f:
                if line.strip():
                    list_analyzed_items.append(line.strip())
    except FileNotFoundError:
        logging.info("vinted_items.txt not found, starting fresh")
    except Exception as e:
        logging.error(e, exc_info=True)
        sys.exit(1)


def save_analyzed_item(item_id):
    try:
        with open("vinted_items.txt", "a") as f:
            f.write(f"{item_id}\n")
    except Exception as e:
        logging.error(e, exc_info=True)


# =========================
# Notifications
# =========================
def send_email(item_title, item_price, item_url, item_image):
    try:
        msg = EmailMessage()
        msg["To"] = Config.smtp_toaddrs
        msg["From"] = email.utils.formataddr(("Vinted Scanner", Config.smtp_username))
        msg["Subject"] = "Vinted Scanner - New Item"
        msg["Date"] = email.utils.formatdate(localtime=True)

        body = f"{item_title}\n{item_price}\n{item_url}\n{item_image}"
        msg.set_content(body)

        with smtplib.SMTP(Config.smtp_server, 587) as server:
            server.starttls()
            server.login(Config.smtp_username, Config.smtp_psw)
            server.send_message(msg)

        logging.info("E-mail sent")

    except Exception as e:
        logging.error(f"Email error: {e}", exc_info=True)


def send_slack_message(item_title, item_price, item_url, item_image):
    if not Config.slack_webhook_url:
        return

    payload = {
        "text": f"*{item_title}*\nPrijs: {item_price}\n{item_url}\n{item_image}"
    }

    try:
        r = requests.post(
            Config.slack_webhook_url,
            json=payload,
            timeout=timeoutconnection,
        )
        if r.status_code != 200:
            logging.error(f"Slack error {r.status_code}: {r.text}")
        else:
            logging.info("Slack notification sent")
    except Exception as e:
        logging.error(f"Slack error: {e}")


def send_telegram_message(item_title, item_price, item_url, item_image):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", Config.telegram_bot_token)
    chat_id = os.getenv("TELEGRAM_CHAT_ID", Config.telegram_chat_id)

    logging.info(
        f"Telegram check | bot_token={'OK' if bot_token else 'MISSING'} | "
        f"chat_id={'OK' if chat_id else 'MISSING'}"
    )

    if not bot_token or not chat_id:
        logging.error("Telegram credentials missing — message NOT sent")
        return

    message = f"<b>{item_title}</b>\nPrijs: {item_price}\n{item_url}\n{item_image}"

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    try:
        r = requests.post(url, json=payload, timeout=timeoutconnection)
        logging.info(f"Telegram HTTP {r.status_code}: {r.text}")
    except Exception as e:
        logging.error(f"Telegram exception: {e}", exc_info=True)



# =========================
# Main
# =========================
def main():
    load_analyzed_item()

send_telegram_message(
    "✅ Vinted scanner is actief",
    "TEST",
    "https://shadowscanner.onrender.com/run",
    "Render + cron-job.org OK"
)


    session = requests.Session()

    try:
        session.post(Config.vinted_url, headers=headers, timeout=timeoutconnection)
    except requests.exceptions.RequestException as e:
        logging.error(f"Session init failed: {e}")
        return

    cookies = session.cookies.get_dict()

    for params in Config.queries:
        try:
            response = requests.get(
                f"{Config.vinted_url}/api/v2/catalog/items",
                params=params,
                cookies=cookies,
                headers=headers,
                timeout=timeoutconnection,
            )
        except requests.exceptions.RequestException as e:
            logging.error(f"Vinted request failed: {e}")
            continue

        data = safe_get_json(response)
        if not data:
            continue

        for item in data.get("items", []):
            item_id = str(item.get("id"))
            if not item_id or item_id in list_analyzed_items:
                continue

            item_title = item.get("title", "Unknown")
            item_url = item.get("url", "")
            price = item.get("price", {})
            item_price = f'{price.get("amount", "?")} {price.get("currency_code", "")}'
            item_image = item.get("photo", {}).get("full_size_url", "")

            if Config.smtp_username and Config.smtp_server:
                send_email(item_title, item_price, item_url, item_image)

            if Config.slack_webhook_url:
                send_slack_message(item_title, item_price, item_url, item_image)

            if bot := os.getenv("TELEGRAM_BOT_TOKEN", Config.telegram_bot_token):
                if Config.telegram_chat_id:
                    send_telegram_message(item_title, item_price, item_url, item_image)

            list_analyzed_items.append(item_id)
            save_analyzed_item(item_id)


if __name__ == "__main__":
    main()

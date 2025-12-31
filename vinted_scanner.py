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

# Configure a rotating file handler to manage log files
handler = RotatingFileHandler("vinted_scanner.log", maxBytes=5000000, backupCount=5)

logging.basicConfig(
    handlers=[handler],
    format="%(asctime)s - %(filename)s - %(funcName)10s():%(lineno)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# Timeout configuration for the requests
timeoutconnection = 30

# List to keep track of already analyzed items
list_analyzed_items = []

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/png,image/svg+xml,*/*;q=0.8",
    "Accept-Language": "nl-NL,nl;q=0.8,en-US;q=0.5,en;q=0.3",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "cross-site",
    "Sec-GPC": "1",
    "Priority": "u=0, i",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
}


def load_analyzed_item():
    """Load previously analyzed item hashes to avoid duplicates."""
    try:
        with open("vinted_items.txt", "r", errors="ignore") as f:
            for line in f:
                if line:
                    list_analyzed_items.append(line.rstrip())
    except IOError as e:
        logging.error(e, exc_info=True)
        sys.exit()


def save_analyzed_item(item_hash):
    """Save a new analyzed item to prevent repeated alerts."""
    try:
        with open("vinted_items.txt", "a") as f:
            f.write(str(item_hash) + "\n")
    except IOError as e:
        logging.error(e, exc_info=True)
        sys.exit()


def send_email(item_title, item_price, item_url, item_image):
    """Send notification e-mail when a new item is found."""
    try:
        msg = EmailMessage()
        msg["To"] = Config.smtp_toaddrs
        msg["From"] = email.utils.formataddr(("Vinted Scanner", Config.smtp_username))
        msg["Subject"] = "Vinted Scanner - New Item"
        msg["Date"] = email.utils.formatdate(localtime=True)
        msg["Message-ID"] = email.utils.make_msgid()

        body = f"{item_title}\n{item_price}\nLink: {item_url}\nImage: {item_image}"
        msg.set_content(body)

        with smtplib.SMTP(Config.smtp_server, 587) as smtpserver:
            smtpserver.ehlo()
            smtpserver.starttls()
            smtpserver.ehlo()
            smtpserver.login(Config.smtp_username, Config.smtp_psw)
            smtpserver.send_message(msg)
            logging.info("E-mail sent")

    except smtplib.SMTPException as e:
        logging.error(f"SMTP error sending email: {e}", exc_info=True)
    except Exception as e:
        logging.error(f"Error sending email: {e}", exc_info=True)


def send_slack_message(item_title, item_price, item_url, item_image):
    """Send a Slack message when a new item is found."""
    webhook_url = Config.slack_webhook_url

    message = f"*{item_title}*\nPrijs: {item_price}\n{item_url}\n{item_image}"
    slack_data = {"text": message}

    try:
        response = requests.post(
            webhook_url,
            data=json.dumps(slack_data),
            headers={"Content-Type": "application/json"},
            timeout=timeoutconnection,
        )

        if response.status_code != 200:
            logging.error(f"Slack notification failed: {response.status_code}, {response.text}")
        else:
            logging.info("Slack notification sent")

    except requests.exceptions.RequestException as e:
        logging.error(f"Error sending Slack message: {e}")


def send_telegram_message(item_title, item_price, item_url, item_image):
    """Send a Telegram message when a new item is found."""

    message = f"<b>{item_title}</b>\nPrijs: {item_price}\n{item_url}\n{item_image}"

    try:
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN", Config.telegram_bot_token)
chat_id = os.getenv("TELEGRAM_CHAT_ID", Config.telegram_chat_id)

url = f"https://api.telegram.org/bot{bot_token}/sendMessage"


        params = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
            "link_preview_options": json.dumps({"is_disabled": True}),
        }

        response = requests.post(url, params=params, headers=headers, timeout=timeoutconnection)
        if response.status_code != 200:
            logging.error(
                f"Telegram notification failed. Status code: {response.status_code}, Response: {response.text}"
            )
        else:
            logging.info("Telegram notification sent")

    except requests.exceptions.RequestException as e:
        logging.error(f"Error sending Telegram message: {e}")


def main():
    load_analyzed_item()

    session = requests.Session()
    session.post(Config.vinted_url, headers=headers, timeout=timeoutconnection)
    cookies = session.cookies.get_dict()

    for params in Config.queries:
        response = requests.get(
            f"{Config.vinted_url}/api/v2/catalog/items", params=params, cookies=cookies, headers=headers
        )
        data = response.json()

        if data:
            for item in data.get("items", []):
                item_id = str(item["id"])
                item_title = item["title"]
                item_url = item["url"]
                item_price = f'{item["price"]["amount"]} {item["price"]["currency_code"]}'
                item_image = item["photo"]["full_size_url"]

                if item_id not in list_analyzed_items:
                    if Config.smtp_username and Config.smtp_server:
                        send_email(item_title, item_price, item_url, item_image)

                    if Config.slack_webhook_url:
                        send_slack_message(item_title, item_price, item_url, item_image)

                    if Config.telegram_bot_token and Config.telegram_chat_id:
                        send_telegram_message(item_title, item_price, item_url, item_image)

                    list_analyzed_items.append(item_id)
                    save_analyzed_item(item_id)


if __name__ == "__main__":
    main()

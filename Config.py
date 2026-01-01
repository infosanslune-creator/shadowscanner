import os


# SMTP Settings for e-mail notification
smtp_username = ""
smtp_psw = ""
smtp_server = ""
smtp_toaddrs = ["User <example@example.com>"]

# Slack WebHook for notification
slack_webhook_url = ""

# Telegram Token and ChatID for notification
telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
gemini_api_key = os.getenv("GEMINI_API_KEY")
# Gemini model name; update if you want another (e.g. gemini-1.5-pro)
gemini_model = "gemini-2.5-flash"

# Vinted URL: use NL site for GPU search
vinted_url = "https://www.vinted.nl"

# Vinted queries for research
# page/per_page/order are usually kept as-is; adjust search_text/brands/price as needed.
queries = [
    {
        "page": "1",
        "per_page": "96",
        "search_text": "",
        "catalog_ids": "",
        "brand_ids[]": [
            "844404",
            "205418",
            "472684",
            "487432",
            "318172",
            "3581848",
            "1439254",
            "132202",
            "891560",
            "268708",
            "94638",
            "58114",
            "162458",
        ],
        "price_from": "200",
        "price_to": "650",
        "currency": "EUR",
        "order": "newest_first",
        "max_pages": 3,
    },
]

# SMTP Settings for e-mail notification
smtp_username = ""
smtp_psw = ""
smtp_server = ""
smtp_toaddrs = ["User <example@example.com>"]

# Slack WebHook for notification
slack_webhook_url = ""

# Telegram Token and ChatID for notification
telegram_bot_token = "8589139226:AAH-QmIrlJOzc83Z7lcm_LFN6NFgWxcubjA"
telegram_chat_id = "1354041534"

# Vinted URL: use NL site for GPU search
vinted_url = "https://www.vinted.nl"

# Vinted queries for research
# page/per_page/order are usually kept as-is; adjust search_text/brands/price as needed.
queries = [
    {
        "page": "1",
        "per_page": "96",
        "search_text": "grafische kaarten",
        "catalog_ids": "",
        # brand_ids[] matches multiple GPU brands from your NL search
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
        "currency": "EUR",
        "order": "newest_first",
    },
]

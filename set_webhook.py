import os
import sys

import httpx

from bot_config import BOT_TOKEN


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python set_webhook.py https://your-domain.com/")
        return 1

    webhook_url = sys.argv[1].strip()
    if not webhook_url.startswith(("https://", "http://")):
        print("Webhook URL must start with https:// or http://")
        return 1

    token = os.getenv("TELEGRAM_BOT_TOKEN", BOT_TOKEN).strip()
    if not token:
        print("Set TELEGRAM_BOT_TOKEN first, or configure it in bot_config.py.")
        return 1

    response = httpx.post(
        f"https://api.telegram.org/bot{token}/setWebhook",
        json={
            "url": webhook_url,
            "allowed_updates": ["chat_join_request", "callback_query", "message"],
        },
        timeout=20,
    )
    response.raise_for_status()
    print(response.json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

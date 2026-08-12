import sys

import httpx

from bot_config import BOT_TOKEN, TARGET_CHAT_ID, target_chat_candidates


def main() -> int:
    if not BOT_TOKEN:
        print("BOT_TOKEN is not configured.")
        return 1
    if not TARGET_CHAT_ID:
        print("TARGET_CHAT_ID is not configured.")
        return 1

    name = " ".join(sys.argv[1:]).strip() or "Secret Key Gate"
    last_data = None
    for chat_id in target_chat_candidates() or {TARGET_CHAT_ID}:
        response = httpx.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/createChatInviteLink",
            json={
                "chat_id": chat_id,
                "name": name,
                "creates_join_request": True,
            },
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        print(data)
        last_data = data
        if data.get("ok") and data.get("result", {}).get("invite_link"):
            print("Approval-required invite link:")
            print(data["result"]["invite_link"])
            return 0

    return 0 if last_data and last_data.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional


# You can set these as environment variables, or place your fixed values here.
FALLBACK_BOT_TOKEN = "8783718667:AAGuPx7c7JpHWXwlICeproOvoa5s_TGyrzo"
FALLBACK_SECRET_PIN = "981239"
FALLBACK_CODE_LINK = "https://t.me/+12202858715"
FALLBACK_TARGET_CHAT_ID = "-4388045069"

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", FALLBACK_BOT_TOKEN).strip()
SECRET_PIN = (os.getenv("SECRET_PIN") or FALLBACK_SECRET_PIN).strip()
CODE_LINK = (os.getenv("CODE_LINK") or FALLBACK_CODE_LINK).strip()
TARGET_CHAT_ID = os.getenv("TARGET_CHAT_ID", FALLBACK_TARGET_CHAT_ID).strip()
PENDING_FILE = Path(os.getenv("PENDING_FILE", "pending_requests.json"))
LAST_UPDATE_FILE = Path(os.getenv("LAST_UPDATE_FILE", "last_update.json"))
KNOWN_USERS_FILE = Path(os.getenv("KNOWN_USERS_FILE", "known_users.json"))

YES_CALLBACK = "secret_key_yes"
NO_CALLBACK = "secret_key_no"
ADMIN_EMAIL = "test@me.com"
ADMIN_PASSWORD = "1234567890"

logger = logging.getLogger(__name__)


def load_pending() -> dict[str, dict[str, Any]]:
    if not PENDING_FILE.exists():
        return {}

    try:
        return json.loads(PENDING_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not read %s: %s", PENDING_FILE, exc)
        return {}


def save_pending(pending: dict[str, dict[str, Any]]) -> None:
    PENDING_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp_file = PENDING_FILE.with_suffix(".tmp")
    temp_file.write_text(
        json.dumps(pending, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temp_file.replace(PENDING_FILE)


def save_last_update(update: dict[str, Any]) -> None:
    LAST_UPDATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    LAST_UPDATE_FILE.write_text(
        json.dumps(update, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def load_known_users() -> dict[str, dict[str, Any]]:
    if not KNOWN_USERS_FILE.exists():
        return {}

    try:
        return json.loads(KNOWN_USERS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not read %s: %s", KNOWN_USERS_FILE, exc)
        return {}


def save_known_users(users: dict[str, dict[str, Any]]) -> None:
    KNOWN_USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp_file = KNOWN_USERS_FILE.with_suffix(".tmp")
    temp_file.write_text(
        json.dumps(users, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temp_file.replace(KNOWN_USERS_FILE)


def remember_user(user: dict[str, Any], chat_id: int, phone_number: str = "") -> None:
    user_id = user.get("id")
    if not user_id:
        return

    users = load_known_users()
    user_key = str(user_id)
    existing = users.get(user_key, {})
    users[user_key] = {
        "id": user_id,
        "chat_id": chat_id,
        "username": user.get("username") or existing.get("username", ""),
        "first_name": user.get("first_name") or existing.get("first_name", ""),
        "last_name": user.get("last_name") or existing.get("last_name", ""),
        "phone_number": phone_number or existing.get("phone_number", ""),
    }
    save_known_users(users)


def target_chat_candidates() -> set[str]:
    if not TARGET_CHAT_ID:
        return set()

    candidates = {TARGET_CHAT_ID}
    if TARGET_CHAT_ID.startswith("-") and not TARGET_CHAT_ID.startswith("-100"):
        candidates.add(f"-100{TARGET_CHAT_ID[1:]}")
    return candidates


def chat_matches_target(chat_id: int) -> bool:
    if not TARGET_CHAT_ID:
        return True
    return str(chat_id) in target_chat_candidates()


def code_link_message() -> str:
    if CODE_LINK:
        return "Use the link below to get the code, then come back here and send it to me."
    return "The code link is not configured yet. Please contact an admin."


def wrong_key_message() -> str:
    if CODE_LINK:
        return "That secret key is not correct. Please try again, or use the code link."
    return "That secret key is not correct. Please try again."


def code_link_url() -> Optional[str]:
    return CODE_LINK or None

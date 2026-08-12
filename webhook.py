import logging
from typing import Any, Optional

import httpx
from flask import Flask, abort, redirect, render_template_string, request, session, url_for

import bot_config as settings


logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = settings.BOT_TOKEN[-32:] or "change-this-secret"


LOGIN_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Bot Admin Login</title>
  <style>
    :root { color-scheme: dark; font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    body { margin: 0; min-height: 100vh; display: grid; place-items: center; background: #0f172a; color: #e5e7eb; }
    main { width: min(92vw, 380px); padding: 28px; background: #111827; border: 1px solid #263244; border-radius: 8px; }
    h1 { margin: 0 0 18px; font-size: 24px; }
    label { display: block; margin: 14px 0 6px; color: #cbd5e1; font-size: 14px; }
    input { width: 100%; box-sizing: border-box; padding: 12px; border: 1px solid #334155; border-radius: 6px; background: #020617; color: #f8fafc; }
    button { width: 100%; margin-top: 18px; padding: 12px; border: 0; border-radius: 6px; background: #7c3aed; color: white; font-weight: 700; cursor: pointer; }
    .error { margin: 0 0 12px; color: #fca5a5; }
  </style>
</head>
<body>
  <main>
    <h1>Bot Admin</h1>
    {% if error %}<p class="error">{{ error }}</p>{% endif %}
    <form method="post">
      <label>Email</label>
      <input name="email" type="email" autocomplete="username" required>
      <label>Password</label>
      <input name="password" type="password" autocomplete="current-password" required>
      <button type="submit">Login</button>
    </form>
  </main>
</body>
</html>
"""


ADMIN_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Bot Admin</title>
  <style>
    :root { color-scheme: dark; font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    body { margin: 0; background: #0f172a; color: #e5e7eb; }
    header { display: flex; justify-content: space-between; align-items: center; padding: 18px 24px; border-bottom: 1px solid #263244; background: #111827; }
    h1 { margin: 0; font-size: 22px; }
    a { color: #a78bfa; text-decoration: none; }
    main { width: min(1080px, calc(100vw - 32px)); margin: 24px auto; display: grid; gap: 18px; }
    section { background: #111827; border: 1px solid #263244; border-radius: 8px; padding: 20px; }
    h2 { margin: 0 0 14px; font-size: 18px; }
    label { display: block; margin: 12px 0 6px; color: #cbd5e1; font-size: 14px; }
    input, textarea { width: 100%; box-sizing: border-box; padding: 12px; border: 1px solid #334155; border-radius: 6px; background: #020617; color: #f8fafc; }
    textarea { min-height: 74px; resize: vertical; }
    button { margin-top: 14px; padding: 11px 14px; border: 0; border-radius: 6px; background: #7c3aed; color: white; font-weight: 700; cursor: pointer; }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 10px; border-bottom: 1px solid #263244; text-align: left; font-size: 14px; }
    th { color: #cbd5e1; }
    .notice { padding: 12px; border-radius: 6px; background: #064e3b; color: #bbf7d0; }
    .error { padding: 12px; border-radius: 6px; background: #7f1d1d; color: #fecaca; }
    .muted { color: #94a3b8; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
    @media (max-width: 780px) { .grid { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <header>
    <h1>Secret-Key Bot Admin</h1>
    <a href="{{ url_for('logout') }}">Logout</a>
  </header>
  <main>
    {% if notice %}<div class="notice">{{ notice }}</div>{% endif %}
    {% if error %}<div class="error">{{ error }}</div>{% endif %}
    <section>
      <h2>Send Verification Prompt</h2>
      <form method="post" action="{{ url_for('admin_send_prompt') }}">
        <label>Telegram user ID, known username, or known phone number</label>
        <input name="recipient" placeholder="5429785922, @username, username, or phone" required>
        <label>Message</label>
        <textarea name="message">Do you have your secret key?</textarea>
        <button type="submit">Send Prompt</button>
      </form>
      <p class="muted">Telegram bots cannot message a random phone number or username. The user must have opened the bot before, or be in a pending join request.</p>
    </section>
    <div class="grid">
      <section>
        <h2>Pending Requests</h2>
        <table>
          <thead><tr><th>User</th><th>Username</th><th>Status</th></tr></thead>
          <tbody>
          {% for user_id, item in pending.items() %}
            <tr><td>{{ user_id }}</td><td>{{ item.username or "" }}</td><td>{{ item.status }}</td></tr>
          {% else %}
            <tr><td colspan="3" class="muted">No pending requests.</td></tr>
          {% endfor %}
          </tbody>
        </table>
      </section>
      <section>
        <h2>Known Users</h2>
        <table>
          <thead><tr><th>User</th><th>Username</th><th>Phone</th></tr></thead>
          <tbody>
          {% for user_id, item in known.items() %}
            <tr><td>{{ user_id }}</td><td>{{ item.username or "" }}</td><td>{{ item.phone_number or "" }}</td></tr>
          {% else %}
            <tr><td colspan="3" class="muted">No known users yet.</td></tr>
          {% endfor %}
          </tbody>
        </table>
      </section>
    </div>
  </main>
</body>
</html>
"""


def telegram_api(method: str, payload: dict[str, Any]) -> dict[str, Any]:
    if not settings.BOT_TOKEN:
        raise RuntimeError("Set TELEGRAM_BOT_TOKEN before using the webhook.")

    response = httpx.post(
        f"https://api.telegram.org/bot{settings.BOT_TOKEN}/{method}",
        json=payload,
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram API error in {method}: {data}")
    return data


def send_message(
    chat_id: int,
    text: str,
    reply_markup: Optional[dict[str, Any]] = None,
) -> None:
    payload: dict[str, Any] = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    telegram_api("sendMessage", payload)


def edit_message_text(
    chat_id: int,
    message_id: int,
    text: str,
    reply_markup: Optional[dict[str, Any]] = None,
) -> None:
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    telegram_api("editMessageText", payload)


def answer_callback_query(callback_query_id: str) -> None:
    telegram_api("answerCallbackQuery", {"callback_query_id": callback_query_id})


def yes_no_markup() -> dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {"text": "Yes", "callback_data": settings.YES_CALLBACK},
                {"text": "No", "callback_data": settings.NO_CALLBACK},
            ]
        ]
    }


def code_link_markup() -> Optional[dict[str, Any]]:
    if not settings.CODE_LINK:
        return None
    return {"inline_keyboard": [[{"text": "Get the code", "url": settings.CODE_LINK}]]}


def force_reply_markup() -> dict[str, Any]:
    return {"force_reply": True, "selective": True}


def normalize_lookup(value: str) -> str:
    return value.strip().lstrip("@").replace(" ", "").casefold()


def target_chat_id() -> int:
    return int(settings.TARGET_CHAT_ID)


def approve_user(user_id: int, chat_id: Optional[int] = None) -> None:
    telegram_api(
        "approveChatJoinRequest",
        {
            "chat_id": chat_id or target_chat_id(),
            "user_id": user_id,
        },
    )


def resolve_recipient(value: str) -> Optional[dict[str, Any]]:
    lookup = normalize_lookup(value)
    if not lookup:
        return None

    pending = settings.load_pending()
    if lookup in pending:
        item = pending[lookup]
        return {
            "user_id": int(lookup),
            "chat_id": int(item.get("user_chat_id") or lookup),
            "pending": item,
        }

    known = settings.load_known_users()
    if lookup in known:
        item = known[lookup]
        return {
            "user_id": int(lookup),
            "chat_id": int(item.get("chat_id") or lookup),
            "known": item,
        }

    for user_id, item in pending.items():
        username = normalize_lookup(str(item.get("username", "")))
        if username and username == lookup:
            return {
                "user_id": int(user_id),
                "chat_id": int(item.get("user_chat_id") or user_id),
                "pending": item,
            }

    for user_id, item in known.items():
        username = normalize_lookup(str(item.get("username", "")))
        phone = normalize_lookup(str(item.get("phone_number", "")))
        if lookup in {username, phone}:
            return {
                "user_id": int(user_id),
                "chat_id": int(item.get("chat_id") or user_id),
                "known": item,
            }

    if lookup.isdigit():
        return {
            "user_id": int(lookup),
            "chat_id": int(lookup),
        }

    return None


def seed_pending_for_prompt(user_id: int, chat_id: int) -> None:
    pending = settings.load_pending()
    known = settings.load_known_users()
    user_key = str(user_id)
    existing = pending.get(user_key, {})
    known_user = known.get(user_key, {})
    pending[user_key] = {
        "chat_id": int(existing.get("chat_id") or target_chat_id()),
        "chat_title": existing.get("chat_title", "Superfans"),
        "user_chat_id": int(existing.get("user_chat_id") or chat_id),
        "username": existing.get("username") or known_user.get("username", ""),
        "first_name": existing.get("first_name") or known_user.get("first_name", ""),
        "last_name": existing.get("last_name") or known_user.get("last_name", ""),
        "status": "awaiting_choice",
        "attempts": int(existing.get("attempts", 0)),
    }
    settings.save_pending(pending)


def require_admin() -> Optional[Any]:
    if session.get("admin_logged_in"):
        return None
    return redirect(url_for("login"))


def handle_join_request(join_request: dict[str, Any]) -> None:
    chat = join_request["chat"]
    chat_id = chat["id"]
    if not settings.chat_matches_target(chat_id):
        logger.info("Ignoring join request for non-target chat %s", chat_id)
        return

    user = join_request["from"]
    settings.remember_user(user, join_request.get("user_chat_id") or user["id"])
    user_key = str(user["id"])
    pending = settings.load_pending()
    pending[user_key] = {
        "chat_id": chat_id,
        "chat_title": chat.get("title", ""),
        "user_chat_id": join_request.get("user_chat_id") or user["id"],
        "username": user.get("username", ""),
        "first_name": user.get("first_name", ""),
        "last_name": user.get("last_name", ""),
        "status": "awaiting_choice",
        "attempts": pending.get(user_key, {}).get("attempts", 0),
    }
    settings.save_pending(pending)

    send_message(
        chat_id=pending[user_key]["user_chat_id"],
        text="Do you have your secret key?",
        reply_markup=yes_no_markup(),
    )


def handle_callback_query(callback_query: dict[str, Any]) -> None:
    answer_callback_query(callback_query["id"])

    user = callback_query["from"]
    user_key = str(user["id"])
    pending = settings.load_pending()
    user_pending = pending.get(user_key)
    message = callback_query.get("message", {})
    message_chat_id = message.get("chat", {}).get("id")
    message_id = message.get("message_id")

    if not message_chat_id or not message_id:
        return

    if not user_pending:
        seed_pending_for_prompt(user["id"], message_chat_id)
        pending = settings.load_pending()
        user_pending = pending.get(user_key)

    if callback_query.get("data") == settings.YES_CALLBACK:
        user_pending["status"] = "awaiting_pin"
        settings.save_pending(pending)
        edit_message_text(
            chat_id=message_chat_id,
            message_id=message_id,
            text="Please send your secret key now.",
        )
        send_message(
            chat_id=user_pending["user_chat_id"],
            text="Reply with your secret key.",
            reply_markup=force_reply_markup(),
        )
        return

    if callback_query.get("data") == settings.NO_CALLBACK:
        user_pending["status"] = "awaiting_code"
        settings.save_pending(pending)
        edit_message_text(
            chat_id=message_chat_id,
            message_id=message_id,
            text=settings.code_link_message(),
            reply_markup=code_link_markup(),
        )


def handle_private_message(message: dict[str, Any]) -> None:
    chat = message.get("chat", {})
    if chat.get("type") != "private":
        return

    user = message.get("from", {})
    user_id = user.get("id")
    if user_id:
        settings.remember_user(user, chat["id"])

    contact = message.get("contact")
    if user_id and contact:
        settings.remember_user(user, chat["id"], contact.get("phone_number", ""))
        send_message(chat_id=chat["id"], text="Your contact has been saved.")
        return

    text = str(message.get("text", "")).strip()
    if not user_id or not text:
        return

    pending = settings.load_pending()
    user_key = str(user_id)
    user_pending = pending.get(user_key)

    if text.casefold().startswith("/start"):
        if user_pending:
            send_message(
                chat_id=chat["id"],
                text="Do you have your secret key?",
                reply_markup=yes_no_markup(),
            )
            return

        send_message(
            chat_id=chat["id"],
            text=(
                "Request to join the group first. I will verify your secret key "
                "here before approving access."
            ),
        )
        return

    if text.startswith("/"):
        send_message(
            chat_id=chat["id"],
            text="Request to join the group, then send your secret key here.",
        )
        return

    if not user_pending:
        if settings.SECRET_PIN and text == settings.SECRET_PIN:
            try:
                approve_user(user_id)
            except Exception as exc:
                logger.exception("Could not approve user without stored pending request.")
                send_message(
                    chat_id=chat["id"],
                    text=(
                        "Your key is correct, but I could not approve the join "
                        f"request automatically: {exc}"
                    ),
                )
                return

            send_message(chat_id=chat["id"], text="Your key is correct. You now have access to the group.")
            return

        send_message(
            chat_id=chat["id"],
            text=(
                "I do not see a pending join request for you. "
                "Please request to join the group first."
            ),
        )
        return

    lower_text = text.casefold()
    if lower_text in {"yes", "y"}:
        user_pending["status"] = "awaiting_pin"
        settings.save_pending(pending)
        send_message(
            chat_id=chat["id"],
            text="Reply with your secret key.",
            reply_markup=force_reply_markup(),
        )
        return

    if lower_text in {"no", "n"}:
        user_pending["status"] = "awaiting_code"
        settings.save_pending(pending)
        send_message(
            chat_id=chat["id"],
            text=settings.code_link_message(),
            reply_markup=code_link_markup(),
        )
        return

    if not settings.SECRET_PIN:
        send_message(chat_id=chat["id"], text="The secret key has not been configured yet.")
        logger.error("SECRET_PIN is not configured.")
        return

    if text != settings.SECRET_PIN:
        user_pending["attempts"] = int(user_pending.get("attempts", 0)) + 1
        user_pending["status"] = "awaiting_pin"
        settings.save_pending(pending)
        send_message(
            chat_id=chat["id"],
            text=settings.wrong_key_message(),
            reply_markup=code_link_markup(),
        )
        return

    approve_user(user_id, user_pending["chat_id"])
    pending.pop(user_key, None)
    settings.save_pending(pending)
    send_message(chat_id=chat["id"], text="Your key is correct. You now have access to the group.")


@app.get("/login")
def login() -> str:
    if session.get("admin_logged_in"):
        return redirect(url_for("admin"))
    return render_template_string(LOGIN_TEMPLATE, error=request.args.get("error", ""))


@app.post("/login")
def login_post() -> Any:
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if email == settings.ADMIN_EMAIL and password == settings.ADMIN_PASSWORD:
        session["admin_logged_in"] = True
        return redirect(url_for("admin"))

    return render_template_string(LOGIN_TEMPLATE, error="Invalid login details."), 401


@app.get("/logout")
def logout() -> Any:
    session.clear()
    return redirect(url_for("login"))


@app.get("/admin")
def admin() -> Any:
    guard = require_admin()
    if guard:
        return guard

    return render_template_string(
        ADMIN_TEMPLATE,
        pending=settings.load_pending(),
        known=settings.load_known_users(),
        notice=request.args.get("notice", ""),
        error=request.args.get("error", ""),
    )


@app.post("/admin/send-prompt")
def admin_send_prompt() -> Any:
    guard = require_admin()
    if guard:
        return guard

    recipient_value = request.form.get("recipient", "")
    message = request.form.get("message", "").strip() or "Do you have your secret key?"
    recipient = resolve_recipient(recipient_value)

    if not recipient:
        return redirect(
            url_for(
                "admin",
                error=(
                    "I could not find that user. Ask them to open the bot and "
                    "send /start first, then try again."
                ),
            )
        )

    try:
        seed_pending_for_prompt(recipient["user_id"], recipient["chat_id"])
        send_message(
            chat_id=recipient["chat_id"],
            text=message,
            reply_markup=yes_no_markup(),
        )
    except Exception as exc:
        logger.exception("Admin prompt failed.")
        return redirect(url_for("admin", error=str(exc)))

    return redirect(url_for("admin", notice="Verification prompt sent."))


@app.get("/")
def health() -> tuple[str, int]:
    return "Telegram bot webhook is ready.", 200


@app.post("/")
@app.post("/telegram-webhook")
def telegram_webhook() -> tuple[str, int]:
    update = request.get_json(silent=True)
    if not isinstance(update, dict):
        abort(400)

    try:
        settings.save_last_update(update)
        logger.info("Received update keys: %s", ", ".join(sorted(update.keys())))
        if "chat_join_request" in update:
            handle_join_request(update["chat_join_request"])
        elif "callback_query" in update:
            handle_callback_query(update["callback_query"])
        elif "message" in update:
            handle_private_message(update["message"])
    except Exception:
        logger.exception("Webhook update failed.")
        return "ok", 200

    return "ok", 200

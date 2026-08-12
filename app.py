

import logging
from typing import Optional
from webhook import app

from telegram import ForceReply, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ChatJoinRequestHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bot_config import (
    BOT_TOKEN,
    CODE_LINK,
    NO_CALLBACK,
    SECRET_PIN,
    YES_CALLBACK,
    chat_matches_target,
    code_link_message,
    load_pending,
    save_pending,
    wrong_key_message,
)

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def question_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Yes", callback_data=YES_CALLBACK),
                InlineKeyboardButton("No", callback_data=NO_CALLBACK),
            ]
        ]
    )


def code_link_keyboard() -> Optional[InlineKeyboardMarkup]:
    if not CODE_LINK:
        return None
    return InlineKeyboardMarkup([[InlineKeyboardButton("Get the code", url=CODE_LINK)]])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not update.effective_message:
        return

    pending = load_pending()
    user_pending = pending.get(str(user.id))

    if user_pending:
        await update.effective_message.reply_text(
            "Do you have your secret key?",
            reply_markup=question_keyboard(),
        )
        return

    await update.effective_message.reply_text(
        "Request to join the group first. I will verify your secret key here "
        "before approving access."
    )


async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    request = update.chat_join_request
    if not request:
        return

    chat_id = request.chat.id
    if not chat_matches_target(chat_id):
        logger.info("Ignoring join request for non-target chat %s", chat_id)
        return

    user = request.from_user
    user_key = str(user.id)
    pending = load_pending()
    pending[user_key] = {
        "chat_id": chat_id,
        "chat_title": request.chat.title or "",
        "user_chat_id": request.user_chat_id or user.id,
        "username": user.username or "",
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
        "status": "awaiting_choice",
        "attempts": pending.get(user_key, {}).get("attempts", 0),
    }
    save_pending(pending)

    await context.bot.send_message(
        chat_id=pending[user_key]["user_chat_id"],
        text="Do you have your secret key?",
        reply_markup=question_keyboard(),
    )


async def handle_key_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.from_user:
        return

    await query.answer()

    pending = load_pending()
    user_key = str(query.from_user.id)
    user_pending = pending.get(user_key)

    if not user_pending:
        await query.edit_message_text(
            "I do not see a pending join request for you. "
            "Please request to join the group first."
        )
        return

    if query.data == YES_CALLBACK:
        user_pending["status"] = "awaiting_pin"
        save_pending(pending)
        await query.edit_message_text("Please send your secret key now.")
        await context.bot.send_message(
            chat_id=user_pending["user_chat_id"],
            text="Reply with your secret key.",
            reply_markup=ForceReply(selective=True),
        )
        return

    if query.data == NO_CALLBACK:
        user_pending["status"] = "awaiting_code"
        save_pending(pending)
        await query.edit_message_text(
            "Use the link below to get the code, then come back here "
            "and send it to me.",
            reply_markup=code_link_keyboard(),
        )


async def handle_private_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if not message or not user or not message.text:
        return

    pending = load_pending()
    user_key = str(user.id)
    user_pending = pending.get(user_key)

    if not user_pending:
        await message.reply_text(
            "I do not see a pending join request for you. "
            "Please request to join the group first."
        )
        return

    text = message.text.strip()
    lower_text = text.casefold()

    if lower_text in {"yes", "y"}:
        user_pending["status"] = "awaiting_pin"
        save_pending(pending)
        await message.reply_text(
            "Reply with your secret key.",
            reply_markup=ForceReply(selective=True),
        )
        return

    if lower_text in {"no", "n"}:
        user_pending["status"] = "awaiting_code"
        save_pending(pending)
        await message.reply_text(
            "Use the link below to get the code, then come back here "
            "and send it to me.",
            reply_markup=code_link_keyboard(),
        )
        return

    if not SECRET_PIN:
        await message.reply_text("The secret key has not been configured yet.")
        logger.error("SECRET_PIN is not configured.")
        return

    if text != SECRET_PIN:
        user_pending["attempts"] = int(user_pending.get("attempts", 0)) + 1
        user_pending["status"] = "awaiting_pin"
        save_pending(pending)
        await message.reply_text(
            "That secret key is not correct. Please try again, or use the code link.",
            reply_markup=code_link_keyboard(),
        )
        return

    try:
        await context.bot.approve_chat_join_request(
            chat_id=user_pending["chat_id"],
            user_id=user.id,
        )
    except TelegramError as exc:
        logger.exception("Could not approve join request for user %s: %s", user.id, exc)
        await message.reply_text(
            "I could not approve your request automatically. Please contact an admin."
        )
        return

    pending.pop(user_key, None)
    save_pending(pending)
    await message.reply_text("Your key is correct. You now have access to the group.")


def build_application() -> Application:
    if not BOT_TOKEN:
        raise RuntimeError("Set TELEGRAM_BOT_TOKEN before starting the bot.")

    return (
        Application.builder()
        .token(BOT_TOKEN)
        .concurrent_updates(False)
        .build()
    )


def main() -> None:
    application = build_application()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(ChatJoinRequestHandler(handle_join_request))
    application.add_handler(CallbackQueryHandler(handle_key_choice))
    application.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND,
            handle_private_text,
        )
    )

    logger.info("Bot is running. Waiting for join requests.")
    application.run_polling(
        allowed_updates=[
            Update.CHAT_JOIN_REQUEST,
            Update.CALLBACK_QUERY,
            Update.MESSAGE,
        ]
    )


if __name__ == "__main__":
    main()

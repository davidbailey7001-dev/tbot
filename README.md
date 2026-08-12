# Telegram Secret-Key Join Bot

This package is ready for cPanel Python App hosting with webhooks.

The bot protects a private Telegram group invite link with a fixed secret PIN:

1. A user taps an approval-required invite link.
2. Telegram places them on the waiting screen.
3. Telegram sends the bot a `chat_join_request`.
4. The bot messages the user: `Do you have your secret key?`
5. `Yes` asks for the PIN.
6. Correct PIN approves the user into the group.
7. `No` sends the user to the configured code link.

## Hard-Coded Settings

The live settings are in `bot_config.py`.

```python
FALLBACK_BOT_TOKEN = "8783718667:..."
FALLBACK_SECRET_PIN = "981239"
FALLBACK_CODE_LINK = "https://t.me/+12202858715"
FALLBACK_TARGET_CHAT_ID = "-4388045069"
```

The admin UI login is:

```text
Email: test@me.com
Password: 1234567890
```

You can change the PIN in `bot_config.py`:

```python
FALLBACK_SECRET_PIN = "your-new-pin"
```

The target chat ID is hard-coded from:

```text
https://web.telegram.org/k/?account=1#-4388045069
```

The bot also accepts Telegram's `-100...` form for the same group if Telegram sends that in webhook updates.

## cPanel Files

Upload these files to:

```text
/home/dexlapro/bots
```

Required:

- `bot_config.py`
- `webhook.py`
- `passenger_wsgi.py`
- `set_webhook.py`
- `create_approval_link.py`
- `requirements.txt`

Optional:

- `bot.py`
- `requirements-polling.txt`
- `README.md`

## cPanel Python App Settings

Use a Python version that has `lswsgi` on this server. From your checks, use Python `3.9`.

```text
Python version: 3.9
Application root: bots
Application URL: bot.dexlapro.com
Application startup file: passenger_wsgi.py
Application Entry point: application
```

Do not use:

```text
Application startup file: bot.py
Application Entry point: bot.py
```

`bot.py` is only for local polling tests and requires Python 3.10+.

## Admin UI

Open:

```text
https://bot.dexlapro.com/login
```

Login with:

```text
test@me.com
1234567890
```

After login, you can send the verification prompt to a known Telegram user.

Accepted recipient values:

- Telegram numeric user ID
- A username the bot has already seen
- A phone number the bot has already seen from a shared Telegram contact

Telegram bots cannot start a private chat with a random phone number or arbitrary username. The user must have opened the bot before, or they must already be in a pending join request.

The prompt has:

- `Yes`: asks for the PIN immediately
- `No`: shows the code link
- Correct PIN/code: approves the pending group join request

## Install On cPanel

From cPanel Terminal:

```bash
cd /home/dexlapro/bots
/home/dexlapro/virtualenv/bots/3.9/bin/python -m pip install -r requirements.txt
/home/dexlapro/virtualenv/bots/3.9/bin/python -m py_compile bot_config.py webhook.py passenger_wsgi.py set_webhook.py create_approval_link.py
touch tmp/restart.txt
```

Then open:

```text
https://bot.dexlapro.com/
```

Expected:

```text
Telegram bot webhook is ready.
```

## Set Webhook

After the website returns ready:

```bash
cd /home/dexlapro/bots
/home/dexlapro/virtualenv/bots/3.9/bin/python set_webhook.py https://bot.dexlapro.com/
```

Expected response:

```text
{'ok': True, 'result': True, 'description': 'Webhook was set'}
```

## Create Approval Link With The Bot

You can create a join-request invite link directly through the Bot API:

```bash
cd /home/dexlapro/bots
/home/dexlapro/virtualenv/bots/3.9/bin/python create_approval_link.py "Secret Key Gate"
```

Share only the returned approval-required invite link.

## Telegram Group Setup

The bot cannot block normal invite links. Telegram must require admin approval on the invite link.

Required group setup:

- Group Type: `Private`
- Old invite links: revoked
- New invite link: `Request Admin Approval` enabled
- Bot is admin
- Bot admin right `Invite Users via Link` enabled
- Members `Add Users` permission disabled
- Chat history for new members: hidden, if you do not want approved users seeing old messages

When the setup is right, users see `Request to Join` or a waiting screen, not instant group access.

## Debugging

Watch logs:

```bash
tail -n 100 /home/dexlapro/bots/stderr.log
```

Check pending join requests received by the bot:

```bash
cat /home/dexlapro/bots/pending_requests.json
```

If the user waits but the bot does not message them:

1. Confirm the webhook is set.
2. Confirm `https://bot.dexlapro.com/` returns ready.
3. Confirm `stderr.log` has no errors.
4. Ask the user to open `t.me/fanhub_ctrl_bot` and press `/start`, then request to join again.

## Local Polling

Only use polling locally or on Python 3.10+:

```bash
python -m pip install -r requirements-polling.txt
python bot.py
```

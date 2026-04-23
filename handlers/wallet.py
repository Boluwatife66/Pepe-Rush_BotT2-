"""
PepeRush Bot — Wallet handler (BONK on Solana)
"""
import re
import logging
from telegram import Update, ForceReply
from telegram.ext import ContextTypes

import database as db
from ui import MAIN_KEYBOARD
from handlers.guard import membership_required

logger = logging.getLogger(__name__)

AWAITING_WALLET = "awaiting_wallet"

# Basic Solana address: 32–44 base58 characters
SOLANA_REGEX = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")


@membership_required
async def wallet_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    db_user = db.get_user(user.id)
    current = db_user["wallet"] or "❌ Not set"

    context.user_data[AWAITING_WALLET] = True

    await update.message.reply_text(
        f"💼 <b>Wallet Settings</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🌐 Network: <b>Solana</b>\n"
        f"🪙 Token: <b>BONK</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 Current wallet:\n<code>{current}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Send your <b>Solana (BONK)</b> wallet address below.\n\n"
        f"⚠️ Make sure it's a valid Solana address!\n"
        f"Type /cancel to go back.",
        parse_mode="HTML",
        reply_markup=ForceReply(selective=True)
    )


async def wallet_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Captures wallet address when user is in wallet-input state."""
    user = update.effective_user

    if not context.user_data.get(AWAITING_WALLET):
        return

    text = update.message.text.strip()

    if text == "/cancel":
        context.user_data.pop(AWAITING_WALLET, None)
        await update.message.reply_text("❌ Cancelled.", reply_markup=MAIN_KEYBOARD)
        return

    if not SOLANA_REGEX.match(text):
        await update.message.reply_text(
            "❌ <b>Invalid Solana Address!</b>\n\n"
            "A valid Solana address is 32–44 characters (base58).\n"
            "Make sure you're copying your <b>BONK wallet</b> address correctly.\n\n"
            "Try again or type /cancel.",
            parse_mode="HTML"
        )
        return

    db.set_wallet(user.id, text)
    context.user_data.pop(AWAITING_WALLET, None)

    await update.message.reply_text(
        f"✅ <b>Wallet Saved!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🌐 Network: <b>Solana</b>\n"
        f"🪙 Token: <b>BONK</b>\n"
        f"📌 Address:\n<code>{text}</code>",
        parse_mode="HTML",
        reply_markup=MAIN_KEYBOARD
    )

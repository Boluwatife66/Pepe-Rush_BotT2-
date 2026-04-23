"""
PepeRush Bot — Withdraw handler
All guards: min balance, cooldown, 1 pending max, wallet, live channel check
"""
import time
import logging

from telegram import Update
from telegram.ext import ContextTypes

import database as db
from config import MIN_WITHDRAW, WITHDRAW_COOLDOWN, ADMIN_ID, PAYOUT_CHANNEL_ID
from ui import MAIN_KEYBOARD, withdraw_confirm_keyboard
from handlers.guard import membership_required

logger = logging.getLogger(__name__)
WITHDRAW_AMOUNT_KEY = "pending_withdraw_amount"


@membership_required
async def withdraw_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    db_user = db.get_user(user.id)

    # Spam guard
    spam = db.get_suspicious_count(user.id, "withdraw_attempt", window=3600)
    if spam >= 5:
        db.log_suspicious(user.id, "withdraw_spam")
        await update.message.reply_text(
            "⚠️ Too many withdrawal attempts. Please wait before trying again.",
            reply_markup=MAIN_KEYBOARD
        )
        return
    db.log_suspicious(user.id, "withdraw_attempt")

    # Wallet required
    wallet = db_user["wallet"]
    if not wallet:
        await update.message.reply_text(
            "❌ <b>No Wallet Set!</b>\n\n"
            "You need to set your <b>Solana (BONK)</b> wallet first.\n"
            "Tap 💼 Wallet to add your address.",
            parse_mode="HTML",
            reply_markup=MAIN_KEYBOARD
        )
        return

    # Min balance
    balance = db_user["balance"]
    if balance < MIN_WITHDRAW:
        needed = MIN_WITHDRAW - balance
        await update.message.reply_text(
            f"❌ <b>Insufficient Balance!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 Your balance: <b>{balance:,} BONK</b>\n"
            f"📉 Minimum: <b>{MIN_WITHDRAW:,} BONK</b>\n"
            f"🔜 Still need: <b>{needed:,} BONK</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 Refer friends to earn more!",
            parse_mode="HTML",
            reply_markup=MAIN_KEYBOARD
        )
        return

    # 1-hour cooldown
    now       = time.time()
    last_wd   = db_user["last_withdraw"] or 0
    elapsed   = now - last_wd
    remaining = WITHDRAW_COOLDOWN - elapsed

    if elapsed < WITHDRAW_COOLDOWN:
        m = int(remaining // 60)
        s = int(remaining % 60)
        await update.message.reply_text(
            f"⏳ <b>Cooldown Active</b>\n\n"
            f"Next withdrawal in: <b>{m}m {s}s</b>",
            parse_mode="HTML",
            reply_markup=MAIN_KEYBOARD
        )
        return

    # 1 pending max
    if db.has_pending_withdrawal(user.id):
        await update.message.reply_text(
            "⏳ <b>Pending Withdrawal Exists</b>\n\n"
            "You already have a pending withdrawal.\n"
            "Wait for it to be processed first.",
            parse_mode="HTML",
            reply_markup=MAIN_KEYBOARD
        )
        return

    # Store and confirm
    context.user_data[WITHDRAW_AMOUNT_KEY] = balance

    await update.message.reply_text(
        f"💸 <b>Withdrawal Confirmation</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 Amount: <b>{balance:,} BONK</b>\n"
        f"🌐 Network: <b>Solana</b>\n"
        f"💼 Wallet:\n<code>{wallet}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ Double-check your wallet address!\n"
        f"Confirm your withdrawal?",
        parse_mode="HTML",
        reply_markup=withdraw_confirm_keyboard()
    )


async def withdraw_confirm_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query  = update.callback_query
    user   = query.from_user
    data   = query.data
    await query.answer()

    if data == "withdraw_cancel":
        context.user_data.pop(WITHDRAW_AMOUNT_KEY, None)
        await query.edit_message_text("❌ Withdrawal cancelled.", reply_markup=None)
        return

    db_user = db.get_user(user.id)
    if not db_user:
        await query.edit_message_text("Session expired. Use /start.")
        return

    amount = context.user_data.pop(WITHDRAW_AMOUNT_KEY, None)
    wallet = db_user["wallet"]

    if not amount or not wallet:
        await query.edit_message_text("❌ Session expired. Please try again.")
        return

    # Race condition guard
    if db_user["balance"] < MIN_WITHDRAW:
        await query.edit_message_text(
            f"❌ Insufficient balance: {db_user['balance']:,} BONK"
        )
        return

    if db.has_pending_withdrawal(user.id):
        await query.edit_message_text("⏳ You already have a pending withdrawal.")
        return

    # Execute
    db.deduct_balance(user.id, amount)
    db.set_last_withdraw(user.id, time.time())
    wd_id = db.create_withdrawal(user.id, amount, wallet)

    # Notify payout channel or admin
    target = PAYOUT_CHANNEL_ID if PAYOUT_CHANNEL_ID else ADMIN_ID
    joined_status = "✅ Verified" if db_user["joined_channels"] else "❌ Not joined"

    try:
        await context.bot.send_message(
            chat_id=target,
            text=(
                f"💸 <b>New Withdrawal Request</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔 User ID: <code>{user.id}</code>\n"
                f"👤 Username: @{user.username or 'N/A'}\n"
                f"💰 Amount: <b>{amount:,} BONK</b>\n"
                f"🌐 Network: <b>Solana</b>\n"
                f"💼 Wallet:\n<code>{wallet}</code>\n"
                f"✅ Channels: {joined_status}\n"
                f"📋 ID: <b>#{wd_id}</b>"
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error("Failed to notify payout target: %s", e)

    await query.edit_message_text(
        "✅ <b>Withdrawal Request Sent!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "💸 Payment processed within <b>1 hour</b>\n"
        "🌐 Network: <b>Solana (BONK)</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ Do NOT leave any required channels\n"
        "or your payment will be <b>cancelled</b>!",
        parse_mode="HTML",
        reply_markup=None
    )
    await context.bot.send_message(
        chat_id=user.id,
        text=f"📊 Remaining balance: <b>{db.get_balance(user.id):,} BONK</b>",
        parse_mode="HTML",
        reply_markup=MAIN_KEYBOARD
    )

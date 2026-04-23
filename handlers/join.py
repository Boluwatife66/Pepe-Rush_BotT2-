"""
PepeRush Bot — Joined button handler + referral reward
"""
import asyncio
import logging
import time

from telegram import Update
from telegram.ext import ContextTypes

import database as db
from channel_checker import check_user_in_all_telegram_channels, invalidate_cache
from config import REFERRAL_REWARD, REFERRAL_DELAY
from ui import MAIN_KEYBOARD

logger = logging.getLogger(__name__)


async def joined_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user  = query.from_user
    await query.answer("🔍 Checking membership…")

    db_user = db.get_user(user.id)
    if not db_user:
        await query.answer("Please use /start first.", show_alert=True)
        return

    if db_user["is_banned"]:
        await query.answer("You are banned.", show_alert=True)
        return

    # Spam guard
    spam = db.get_suspicious_count(user.id, "join_spam", window=300)
    if spam >= 8:
        await query.answer("⚠️ Too many attempts. Wait a few minutes.", show_alert=True)
        return
    db.log_suspicious(user.id, "join_spam")

    # Live Telegram channel check
    invalidate_cache(user.id)
    all_joined, failed = await check_user_in_all_telegram_channels(context.bot, user.id)

    if not all_joined and failed:
        await query.answer(
            "❌ You haven't joined all required Telegram channels yet!\n\n"
            "Join them all then tap verify again.",
            show_alert=True
        )
        return

    # Mark joined
    db.set_joined_channels(user.id, 1)

    await query.edit_message_text(
        "✅ <b>Membership Verified!</b>\n\n"
        "Welcome to PepeRush Bot 🐸\n"
        "Start earning BONK now!",
        parse_mode="HTML"
    )
    await context.bot.send_message(
        chat_id=user.id,
        text=(
            "🎉 <b>You're in!</b>\n\n"
            f"💰 Balance: <b>{db.get_balance(user.id):,} BONK</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📌 Use the menu to earn more!"
        ),
        parse_mode="HTML",
        reply_markup=MAIN_KEYBOARD
    )

    # Schedule referral reward with delay
    pending = db.get_referral_pending(user.id)
    if pending and not db.is_referral_rewarded(user.id):
        context.application.create_task(
            _grant_referral_delayed(context, user.id, pending["referrer_id"])
        )


async def _grant_referral_delayed(context, new_user_id: int, referrer_id: int):
    await asyncio.sleep(REFERRAL_DELAY)

    # Re-validate
    db_user = db.get_user(new_user_id)
    if not db_user or not db_user["joined_channels"] or db_user["is_banned"]:
        logger.info("Referral skipped — new user %s invalid state", new_user_id)
        return

    if db.is_referral_rewarded(new_user_id):
        return

    # Re-check channels one more time (anti-fake)
    ok, _ = await check_user_in_all_telegram_channels(context.bot, new_user_id)
    if not ok:
        logger.info("Referral skipped — user %s left channels", new_user_id)
        return

    db.add_balance(referrer_id, REFERRAL_REWARD)
    db.mark_referral_rewarded(new_user_id, referrer_id)

    new_user = db.get_user(new_user_id)
    new_bal  = db.get_balance(referrer_id)

    try:
        await context.bot.send_message(
            chat_id=referrer_id,
            text=(
                "🎉 <b>Referral Reward!</b>\n\n"
                f"👤 {new_user['first_name']} (@{new_user['username'] or 'N/A'}) "
                f"joined and verified!\n"
                f"💰 +<b>{REFERRAL_REWARD:,} BONK</b> credited!\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"📊 New Balance: <b>{new_bal:,} BONK</b>"
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.warning("Could not notify referrer %s: %s", referrer_id, e)

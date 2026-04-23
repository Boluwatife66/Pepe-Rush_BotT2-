"""
PepeRush Bot — /start handler
"""
import asyncio
import logging
import time

from telegram import Update
from telegram.ext import ContextTypes

import database as db
from config import WARNING_TEXT, REFERRAL_DELAY, REFERRAL_REWARD
from ui import MAIN_KEYBOARD, human_check_keyboard, joined_keyboard
from channel_checker import enforce_membership, invalidate_cache

logger = logging.getLogger(__name__)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # Block bots
    if user.is_bot:
        return

    # Require username
    if not user.username:
        await update.message.reply_text(
            "❌ <b>Username Required</b>\n\n"
            "You need a Telegram username to use PepeRush Bot.\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Go to: <i>Settings → Edit Profile → Username</i>\n"
            "Then come back and tap /start again.",
            parse_mode="HTML"
        )
        return

    db.upsert_user(user.id, user.username, user.first_name)
    db_user = db.get_user(user.id)

    if db_user["is_banned"]:
        await update.message.reply_text("🚫 You are banned from PepeRush Bot.")
        return

    # Parse referral
    args = context.args
    if args:
        try:
            ref_id = int(args[0])
            if ref_id != user.id:
                referrer = db.get_user(ref_id)
                if referrer and not db_user["referrer_id"]:
                    db.set_referrer(user.id, ref_id)
                    db.add_referral_pending(user.id, ref_id)
            else:
                db.log_suspicious(user.id, "self_referral_attempt")
        except (ValueError, TypeError):
            pass

    # Human captcha
    if not db_user["human_verified"]:
        await update.message.reply_text(
            "🐸 <b>Welcome to PepeRush Bot!</b>\n\n"
            "Earn <b>BONK</b> on Solana by inviting friends\n"
            "and completing daily tasks!\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "First, please verify you are human 👇",
            parse_mode="HTML",
            reply_markup=human_check_keyboard()
        )
        return

    # Join wall
    if not db_user["joined_channels"]:
        await _show_join_wall(update)
        return

    # Re-check membership even for returning users
    invalidate_cache(user.id)
    ok, err = await enforce_membership(context.bot, user.id)
    if not ok:
        await update.message.reply_text(err, parse_mode="HTML")
        await _show_join_wall(update)
        return

    await update.message.reply_text(
        f"🐸 <b>Welcome back, {user.first_name}!</b>\n\n"
        f"💰 Balance: <b>{db.get_balance(user.id):,} BONK</b>\n"
        f"👥 Referrals: <b>{db_user['referral_count']}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Use the menu below to earn more BONK 🚀",
        parse_mode="HTML",
        reply_markup=MAIN_KEYBOARD
    )


async def human_verification_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user  = query.from_user
    await query.answer("Verifying…")

    if user.is_bot or not user.username:
        await query.edit_message_text("❌ You need a Telegram username to use this bot.")
        return

    db.set_human_verified(user.id)
    db_user = db.get_user(user.id)

    if not db_user["joined_channels"]:
        await query.edit_message_text(
            "✅ <b>Human verification passed!</b>\n\n"
            "Now join all required channels below 👇",
            parse_mode="HTML"
        )
        tasks = db.get_active_tasks()
        await context.bot.send_message(
            chat_id=user.id,
            text=WARNING_TEXT,
            parse_mode="HTML"
        )
        await context.bot.send_message(
            chat_id=user.id,
            text=(
                "📋 <b>Required Channels & Groups</b>\n\n"
                "Join <b>ALL</b> of them then tap verify 👇"
            ),
            parse_mode="HTML",
            reply_markup=joined_keyboard(tasks)
        )
    else:
        await query.edit_message_text("✅ All done!")
        await context.bot.send_message(
            chat_id=user.id,
            text=f"🐸 Welcome back, <b>{user.first_name}</b>!",
            parse_mode="HTML",
            reply_markup=MAIN_KEYBOARD
        )


async def _show_join_wall(update: Update):
    tasks = db.get_active_tasks()
    await update.message.reply_text(WARNING_TEXT, parse_mode="HTML")
    await update.message.reply_text(
        "📋 <b>Required Channels & Groups</b>\n\n"
        "You must join <b>ALL</b> of them to use PepeRush Bot.\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "After joining everything, tap <b>✅ I Have Joined All</b>",
        parse_mode="HTML",
        reply_markup=joined_keyboard(tasks)
    )

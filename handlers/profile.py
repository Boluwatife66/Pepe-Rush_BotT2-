"""
PepeRush Bot — Profile handler
"""
from telegram import Update
from telegram.ext import ContextTypes

import database as db
from ui import MAIN_KEYBOARD
from handlers.guard import membership_required


@membership_required
async def profile_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    db_user = db.get_user(user.id)

    bot_info = await context.bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user.id}"
    wallet   = db_user["wallet"] or "❌ Not set"
    earned   = db_user["referral_count"] * 10_000

    await update.message.reply_text(
        f"📊 <b>Your PepeRush Profile</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 Name: <b>{user.first_name}</b>\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"💰 Balance: <b>{db_user['balance']:,} BONK</b>\n"
        f"👥 Referrals: <b>{db_user['referral_count']}</b>\n"
        f"💎 Earned from referrals: <b>{earned:,} BONK</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💼 Wallet (Solana):\n<code>{wallet}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 Your referral link:\n<code>{ref_link}</code>",
        parse_mode="HTML",
        reply_markup=MAIN_KEYBOARD
    )

"""
PepeRush Bot — Referral handler
"""
from telegram import Update
from telegram.ext import ContextTypes

import database as db
from config import REFERRAL_REWARD, REFERRAL_DELAY
from ui import MAIN_KEYBOARD
from handlers.guard import membership_required


@membership_required
async def referral_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    db_user = db.get_user(user.id)

    bot_info  = await context.bot.get_me()
    ref_link  = f"https://t.me/{bot_info.username}?start={user.id}"
    ref_count = db_user["referral_count"]
    earned    = ref_count * REFERRAL_REWARD

    await update.message.reply_text(
        f"👥 <b>Referral System</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 Per referral: <b>{REFERRAL_REWARD:,} BONK</b>\n"
        f"👥 Your referrals: <b>{ref_count}</b>\n"
        f"💎 Total earned: <b>{earned:,} BONK</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 <b>Your Referral Link:</b>\n"
        f"<code>{ref_link}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>Rules:</b>\n"
        f"• Friend must join ALL required channels\n"
        f"• Friend must tap ✅ Joined\n"
        f"• Reward credited after {REFERRAL_DELAY}s anti-bot delay\n"
        f"• Self-referral is blocked\n"
        f"• Duplicate rewards blocked",
        parse_mode="HTML",
        reply_markup=MAIN_KEYBOARD
    )

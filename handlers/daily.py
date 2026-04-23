"""
PepeRush Bot — Daily Bonus handler
"""
import time
from telegram import Update
from telegram.ext import ContextTypes

import database as db
from config import DAILY_BONUS, DAILY_COOLDOWN
from ui import MAIN_KEYBOARD
from handlers.guard import membership_required


@membership_required
async def daily_bonus_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    db_user = db.get_user(user.id)

    now       = time.time()
    last      = db_user["last_daily"] or 0
    elapsed   = now - last
    remaining = DAILY_COOLDOWN - elapsed

    if elapsed < DAILY_COOLDOWN:
        h = int(remaining // 3600)
        m = int((remaining % 3600) // 60)
        s = int(remaining % 60)
        await update.message.reply_text(
            f"⏳ <b>Already Claimed!</b>\n\n"
            f"Next bonus in: <b>{h:02d}h {m:02d}m {s:02d}s</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 Current balance: <b>{db_user['balance']:,} BONK</b>",
            parse_mode="HTML",
            reply_markup=MAIN_KEYBOARD
        )
        return

    db.add_balance(user.id, DAILY_BONUS)
    db.set_last_daily(user.id, now)
    new_balance = db.get_balance(user.id)

    await update.message.reply_text(
        f"🎁 <b>Daily Bonus Claimed!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 +<b>{DAILY_BONUS:,} BONK</b> added!\n"
        f"📊 New Balance: <b>{new_balance:,} BONK</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🕐 Come back in 24 hours for more! 🐸",
        parse_mode="HTML",
        reply_markup=MAIN_KEYBOARD
    )

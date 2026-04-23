"""
PepeRush Bot — Leaderboard handler
"""
from telegram import Update
from telegram.ext import ContextTypes

import database as db
from ui import MAIN_KEYBOARD
from handlers.guard import membership_required

MEDALS = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]


@membership_required
async def leaderboard_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = db.get_leaderboard(10)

    if not rows:
        await update.message.reply_text(
            "🏆 <b>Leaderboard</b>\n\nNo referrals yet — be the first! 🐸",
            parse_mode="HTML",
            reply_markup=MAIN_KEYBOARD
        )
        return

    lines = ["🏆 <b>Top 10 Inviters</b>\n━━━━━━━━━━━━━━━━━━━━\n"]
    for i, row in enumerate(rows):
        medal = MEDALS[i] if i < len(MEDALS) else f"{i+1}."
        name  = row["first_name"] or "Unknown"
        uname = f"@{row['username']}" if row["username"] else ""
        count = row["referral_count"]
        bonk  = count * 10_000
        lines.append(f"{medal} <b>{name}</b> {uname}\n    👥 {count} refs • 💰 {bonk:,} BONK")

    lines.append("\n━━━━━━━━━━━━━━━━━━━━")
    lines.append("🔗 Invite friends to climb the board!")

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=MAIN_KEYBOARD
    )

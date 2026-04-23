"""
PepeRush Bot — UI / Keyboards
"""
from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["📊 Profile", "👥 Referral"],
        ["🎁 Daily Bonus", "🏆 Leaderboard"],
        ["💼 Wallet", "💸 Withdraw"],
    ],
    resize_keyboard=True,
    one_time_keyboard=False,
)

def human_check_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ I am Human — Tap to Verify", callback_data="human_check")
    ]])

def joined_keyboard(tasks: list) -> InlineKeyboardMarkup:
    buttons = []
    tg  = [t for t in tasks if t["platform"] == "telegram"]
    wa  = [t for t in tasks if t["platform"] == "whatsapp"]
    for i, t in enumerate(tg, 1):
        buttons.append([InlineKeyboardButton(f"📢 Join Telegram Channel {i}", url=t["link"])])
    for i, t in enumerate(wa, 1):
        buttons.append([InlineKeyboardButton(f"💬 Join WhatsApp Group {i}", url=t["link"])])
    buttons.append([InlineKeyboardButton("✅ I Have Joined All — Verify Now", callback_data="joined")])
    return InlineKeyboardMarkup(buttons)

def withdraw_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Confirm Withdraw", callback_data="withdraw_confirm"),
        InlineKeyboardButton("❌ Cancel",            callback_data="withdraw_cancel"),
    ]])

def divider() -> str:
    return "━━━━━━━━━━━━━━━━━━━━"

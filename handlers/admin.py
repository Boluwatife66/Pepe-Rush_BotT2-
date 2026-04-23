"""
PepeRush Bot — Admin Commands
/admin_stats, /add_task, /remove_task, /add_balance, /getchatid, /ban
"""
import asyncio
import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import TelegramError

import database as db
from config import ADMIN_ID

logger = logging.getLogger(__name__)


def _admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


# ── /admin_stats ──────────────────────────────────────────────────────────────

async def admin_stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _admin(update.effective_user.id):
        await update.message.reply_text("⛔ Unauthorised.")
        return

    stats = db.get_stats()
    tasks = db.get_active_tasks()
    tg = [t for t in tasks if t["platform"] == "telegram"]
    wa = [t for t in tasks if t["platform"] == "whatsapp"]

    task_lines = "\n".join(
        f"  {'📢' if t['platform']=='telegram' else '💬'} {t['link'][:50]}{'…' if len(t['link'])>50 else ''}"
        f"{' ✅' if t['chat_id'] else ' ⚠️ no chat_id'}"
        for t in tasks
    )

    await update.message.reply_text(
        f"📊 <b>PepeRush Admin Dashboard</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Total Users: <b>{stats['total_users']:,}</b>\n"
        f"💸 Total Withdrawals: <b>{stats['total_withdrawals']:,}</b>\n"
        f"⏳ Pending: <b>{stats['pending_withdrawals']:,}</b>\n"
        f"💰 BONK Paid Out: <b>{stats['total_pepe_out']:,}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📢 Telegram Tasks: {len(tg)} | 💬 WhatsApp: {len(wa)}\n\n"
        f"<b>Active Tasks:</b>\n{task_lines}",
        parse_mode="HTML"
    )


# ── /getchatid <link> ─────────────────────────────────────────────────────────

async def get_chat_id_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _admin(update.effective_user.id):
        await update.message.reply_text("⛔ Unauthorised.")
        return

    args = context.args
    if not args:
        await update.message.reply_text("Usage: /getchatid <invite_link>")
        return

    link = args[0]
    await update.message.reply_text("🔍 Fetching chat info…")

    try:
        chat = await context.bot.get_chat(link)
        sql  = f"UPDATE tasks SET chat_id = '{chat.id}' WHERE link = '{link}';"
        await update.message.reply_text(
            f"✅ <b>Chat Found!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📢 Title: <b>{chat.title}</b>\n"
            f"🆔 Chat ID: <code>{chat.id}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Run this SQL in DB Browser:\n"
            f"<code>{sql}</code>\n\n"
            f"Or use /setchatid {link} {chat.id}",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ Failed to fetch: <code>{e}</code>\n\n"
            f"Make sure the bot is admin in that channel.",
            parse_mode="HTML"
        )


# ── /setchatid <link> <chat_id> ───────────────────────────────────────────────

async def set_chat_id_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _admin(update.effective_user.id):
        await update.message.reply_text("⛔ Unauthorised.")
        return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: /setchatid <link> <chat_id>")
        return

    link    = args[0]
    chat_id = args[1]
    db.update_task_chat_id(link, chat_id)
    await update.message.reply_text(
        f"✅ Chat ID set!\n\n<code>{link}</code>\n→ <code>{chat_id}</code>",
        parse_mode="HTML"
    )


# ── /add_task <platform> <link> ───────────────────────────────────────────────

async def add_task_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _admin(update.effective_user.id):
        await update.message.reply_text("⛔ Unauthorised.")
        return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "Usage:\n/add_task telegram <link>\n/add_task whatsapp <link>"
        )
        return

    platform = args[0].lower()
    link     = args[1]

    if platform not in ("telegram", "whatsapp"):
        await update.message.reply_text("❌ Platform must be 'telegram' or 'whatsapp'.")
        return

    # Auto-fetch chat_id for Telegram
    chat_id = None
    if platform == "telegram":
        try:
            chat    = await context.bot.get_chat(link)
            chat_id = str(chat.id)
            await update.message.reply_text(
                f"✅ Channel found: <b>{chat.title}</b>\n"
                f"🆔 Chat ID: <code>{chat_id}</code>",
                parse_mode="HTML"
            )
        except Exception as e:
            await update.message.reply_text(
                f"⚠️ Could not auto-fetch chat ID: {e}\n"
                f"Task added without verification — use /setchatid to fix."
            )

    db.add_task(platform, link, chat_id)

    # Broadcast + reset for Telegram channels
    if platform == "telegram":
        await update.message.reply_text("📢 Broadcasting to all users…")
        user_ids = db.get_all_user_ids()
        sent, failed = 0, 0

        for uid in user_ids:
            try:
                await context.bot.send_message(
                    chat_id=uid,
                    text=(
                        f"📢 <b>New Required Channel!</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"Join now to stay eligible for withdrawals:\n"
                        f"{link}\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"⚠️ <b>This is now mandatory.</b>\n"
                        f"Not joining = withdrawal blocked!"
                    ),
                    parse_mode="HTML"
                )
                sent += 1
            except TelegramError:
                failed += 1
            await asyncio.sleep(0.05)

        # Reset all users — must re-verify
        db.reset_all_joined()

        await update.message.reply_text(
            f"✅ <b>Done!</b>\n"
            f"📨 Sent: {sent} | ❌ Failed: {failed}\n"
            f"🔒 All users reset — must re-verify membership."
        )
    else:
        await update.message.reply_text(f"✅ WhatsApp task added:\n{link}")


# ── /remove_task <link> ───────────────────────────────────────────────────────

async def remove_task_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _admin(update.effective_user.id):
        await update.message.reply_text("⛔ Unauthorised.")
        return

    args = context.args
    if not args:
        await update.message.reply_text("Usage: /remove_task <link>")
        return

    db.remove_task(args[0])
    await update.message.reply_text(f"✅ Task removed:\n{args[0]}")


# ── /add_balance <user_id> <amount> ──────────────────────────────────────────

async def add_balance_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _admin(update.effective_user.id):
        await update.message.reply_text("⛔ Unauthorised.")
        return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: /add_balance <user_id> <amount>")
        return

    try:
        target_id = int(args[0])
        amount    = int(args[1])
    except ValueError:
        await update.message.reply_text("❌ user_id and amount must be integers.")
        return

    if amount <= 0:
        await update.message.reply_text("❌ Amount must be positive.")
        return

    target = db.get_user(target_id)
    if not target:
        await update.message.reply_text(f"❌ User {target_id} not found.")
        return

    db.add_balance(target_id, amount)
    new_bal = db.get_balance(target_id)

    await update.message.reply_text(
        f"✅ Added <b>{amount:,} BONK</b> to <code>{target_id}</code>\n"
        f"New balance: <b>{new_bal:,} BONK</b>",
        parse_mode="HTML"
    )

    try:
        await context.bot.send_message(
            chat_id=target_id,
            text=(
                f"🎁 <b>Admin Balance Top-Up!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"💰 +<b>{amount:,} BONK</b> added!\n"
                f"📊 New Balance: <b>{new_bal:,} BONK</b> 🐸"
            ),
            parse_mode="HTML"
        )
    except TelegramError:
        pass


# ── /ban <user_id> ────────────────────────────────────────────────────────────

async def ban_user_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _admin(update.effective_user.id):
        await update.message.reply_text("⛔ Unauthorised.")
        return

    args = context.args
    if not args:
        await update.message.reply_text("Usage: /ban <user_id>")
        return

    try:
        target_id = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ user_id must be an integer.")
        return

    db.ban_user(target_id)
    await update.message.reply_text(f"🚫 User <code>{target_id}</code> has been banned.", parse_mode="HTML")

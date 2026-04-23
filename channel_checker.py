"""
PepeRush Bot — Channel Verification
enforce_membership() is called on EVERY user action.
"""
import logging
import asyncio
from telegram import Bot
from telegram.error import TelegramError
import database as db

logger = logging.getLogger(__name__)

# Cache: {user_id: (result, timestamp)}  — 60-second TTL to avoid rate limits
_cache: dict = {}
CACHE_TTL = 60


async def check_user_in_all_telegram_channels(bot: Bot, user_id: int) -> tuple[bool, list]:
    """Returns (all_joined, failed_links). Skips channels without chat_id."""
    tasks = db.get_telegram_tasks()
    verifiable = [t for t in tasks if t["chat_id"]]

    if not verifiable:
        return True, []

    async def check_one(task):
        try:
            member = await bot.get_chat_member(chat_id=task["chat_id"], user_id=user_id)
            if member.status in ("left", "kicked", "banned"):
                return task["link"]
        except TelegramError as e:
            logger.warning("getChatMember error %s / %s: %s", task["chat_id"], user_id, e)
        return None

    results = await asyncio.gather(*[check_one(t) for t in verifiable])
    failed = [r for r in results if r]
    return len(failed) == 0, failed


async def enforce_membership(bot: Bot, user_id: int) -> tuple[bool, str]:
    """
    Fast membership re-check with 60s cache.
    Resets joined_channels=0 if user left any channel.
    Returns (ok, error_message).
    """
    import time
    now = time.time()

    # Check cache
    cached = _cache.get(user_id)
    if cached:
        result, ts = cached
        if now - ts < CACHE_TTL:
            return result

    all_joined, failed = await check_user_in_all_telegram_channels(bot, user_id)

    if not all_joined and failed:
        db.set_joined_channels(user_id, 0)
        db.log_suspicious(user_id, "left_required_channel")
        _cache[user_id] = ((False, (
            "🚫 <b>Access Blocked!</b>\n\n"
            "You have left one or more required channels.\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👉 Use /start to rejoin and restore access.\n"
            "⚠️ Withdrawals are frozen until you comply."
        )), now)
        return False, (
            "🚫 <b>Access Blocked!</b>\n\n"
            "You have left one or more required channels.\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👉 Use /start to rejoin and restore access.\n"
            "⚠️ Withdrawals are frozen until you comply."
        )

    _cache[user_id] = ((True, ""), now)
    return True, ""


def invalidate_cache(user_id: int):
    _cache.pop(user_id, None)

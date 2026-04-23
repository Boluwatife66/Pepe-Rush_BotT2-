"""
PepeRush Bot — Universal Membership Guard
Wraps every handler to enforce channel membership on every action.
"""
import functools
import logging
from telegram import Update
from telegram.ext import ContextTypes

import database as db
from channel_checker import enforce_membership
from ui import MAIN_KEYBOARD

logger = logging.getLogger(__name__)


def membership_required(func):
    """
    Decorator: checks user exists, is verified, has joined channels,
    and is still a member of all channels — on EVERY command/button.
    """
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user:
            return

        db_user = db.get_user(user.id)
        if not db_user:
            msg = update.message or (update.callback_query and update.callback_query.message)
            if msg:
                await msg.reply_text("Please use /start to begin.")
            return

        if db_user["is_banned"]:
            msg = update.message or (update.callback_query and update.callback_query.message)
            if msg:
                await msg.reply_text("🚫 You are banned from PepeRush Bot.")
            return

        if not db_user["human_verified"] or not db_user["joined_channels"]:
            msg = update.message or (update.callback_query and update.callback_query.message)
            if msg:
                await msg.reply_text(
                    "⚠️ Please complete onboarding first.\nUse /start to begin.",
                    reply_markup=MAIN_KEYBOARD
                )
            return

        # Live membership check
        ok, err = await enforce_membership(context.bot, user.id)
        if not ok:
            msg = update.message or (update.callback_query and update.callback_query.message)
            if msg:
                await msg.reply_text(err, parse_mode="HTML", reply_markup=MAIN_KEYBOARD)
            return

        return await func(update, context)
    return wrapper

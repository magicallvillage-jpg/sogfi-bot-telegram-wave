import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import AUTHORIZED_USERS
from db import uploader_collection, is_uploader

logger = logging.getLogger(__name__)

async def add_uploader_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in AUTHORIZED_USERS:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    target_user_id = None
    if update.message.reply_to_message:
        target_user_id = update.message.reply_to_message.from_user.id
    elif context.args:
        try:
            target_user_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("⚠️ Please provide a valid user ID.")
            return

    if not target_user_id:
        await update.message.reply_text("ℹ️ Usage: Reply to a user or provide their user ID.")
        return

    if await is_uploader(target_user_id):
        await update.message.reply_text(f"ℹ️ User ID {target_user_id} is already an uploader.")
    else:
        await uploader_collection.insert_one({"user_id": target_user_id})
        await update.message.reply_text(f"✅ User ID {target_user_id} added as an uploader.")
        logger.info(f"Uploader added: {target_user_id} by {user_id}")

async def remove_uploader_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in AUTHORIZED_USERS:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    target_user_id = None
    if update.message.reply_to_message:
        target_user_id = update.message.reply_to_message.from_user.id
    elif context.args:
        try:
            target_user_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("⚠️ Please provide a valid user ID.")
            return

    if not target_user_id:
        await update.message.reply_text("ℹ️ Usage: Reply to a user or provide their user ID.")
        return

    result = await uploader_collection.delete_one({"user_id": target_user_id})
    if result.deleted_count > 0:
        await update.message.reply_text(f"✅ User ID {target_user_id} removed from uploaders.")
        logger.info(f"Uploader removed: {target_user_id} by {user_id}")
    else:
        await update.message.reply_text(f"ℹ️ User ID {target_user_id} is not an uploader.")

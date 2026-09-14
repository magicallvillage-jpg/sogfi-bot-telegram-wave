import aiohttp
import logging
from telegram.ext import ApplicationBuilder, CommandHandler, InlineQueryHandler, CallbackQueryHandler
from telegram import BotCommand
from config import BOT_TOKEN
from handlers.uploader import upload_command, update_command
from handlers.custome import custome_command, custome_update_command
from handlers.admin import add_uploader_command, remove_uploader_command
from handlers.inline import inlinequery
from handlers.attachments import (
    attach_command, 
    detach_command, 
    list_attachments_command, 
    list_all_attachments_command,
    attachment_stats_command,
    handle_attachment_callbacks
)

CATBOX_API_URL = "https://catbox.moe/user/api.php"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start_command(update, context):
    await update.message.reply_text("Hi! I'm your Uploader Bot, exclusively for admins. Use /help to get started!")

async def help_command(update, context):
    await update.message.reply_text(
        "/upload - Upload a new entry with an image and details (photo + caption format)\n"
        "/update <id> <field> <new_value> - Update entry details\n"
        "/add_uploader - Add an uploader (admin only)\n"
        "/remove_uploader - Remove an uploader (admin only)\n"
        "/custome - Upload a custom character (sudo users only)\n"
        "/custome_update <id> <field> <new_value> - Update custom character details (sudo users only)\n"
        "/link - Upload a replied image/video to Catbox and get the link\n"
        "/search - Search characters inline\n"
        "/attach <character_id> <attached_character_id> - Attach one character to another\n"
        "/detach <character_id> <attached_character_id> - Detach a character from another\n"
        "/list_attachments <character_id> - List the attached character\n"
        "/list_all_attachments [page_number] - List all character attachments\n"
        "/attachment_stats - Show attachment statistics\n"
        "/delete <character_id> - Delete a character"
    )

async def link_command(update, context):
    replied_message = update.message.reply_to_message

    if not replied_message or (not replied_message.photo and not replied_message.video):
        await update.message.reply_text("Please reply to a message that contains an image or video.")
        return

    # Determine file type
    media = replied_message.photo[-1] if replied_message.photo else replied_message.video
    media_file = await context.bot.get_file(media.file_id)
    
    async with aiohttp.ClientSession() as session:
        async with session.get(media_file.file_path) as response:
            media_bytes = await response.read()
        
        # Upload to Catbox (for both images and videos)
        catbox_data = aiohttp.FormData()
        catbox_data.add_field("reqtype", "fileupload")
        catbox_data.add_field("fileToUpload", media_bytes, filename=media_file.file_path.split("/")[-1])

        async with session.post(CATBOX_API_URL, data=catbox_data) as catbox_response:
            if catbox_response.status == 200:
                catbox_url = await catbox_response.text()
                await update.message.reply_text(f"Here is your Catbox link: {catbox_url.strip()}")
            else:
                await update.message.reply_text("Failed to upload to Catbox.")

async def set_bot_commands(application):
    """Set the bot's command menu in Telegram."""
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("help", "Show available commands"),
        BotCommand("upload", "Upload a new character"),
        BotCommand("update", "Update a character's details"),
        BotCommand("add_uploader", "Add an uploader (admin only)"),
        BotCommand("remove_uploader", "Remove an uploader (admin only)"),
        BotCommand("custome", "Upload a custom character (sudo users only)"),
        BotCommand("custome_update", "Update a custom character's details (sudo users only)"),
        BotCommand("link", "Upload a replied image/video to Catbox"),
        BotCommand("search", "Search characters inline"),
        BotCommand("attach", "Attach one character to another"),
        BotCommand("detach", "Detach a character from another"),
        BotCommand("list_attachments", "List the attached character"),
        BotCommand("list_all_attachments", "List all character attachments"),
        BotCommand("attachment_stats", "Show attachment statistics"),
        BotCommand("delete", "Delete a character")
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Bot commands set successfully.")

def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("upload", upload_command))
    application.add_handler(CommandHandler("update", update_command))
    application.add_handler(CommandHandler("add_uploader", add_uploader_command))
    application.add_handler(CommandHandler("remove_uploader", remove_uploader_command))
    application.add_handler(CommandHandler("custome", custome_command))
    application.add_handler(CommandHandler("custome_update", custome_update_command))
    application.add_handler(CommandHandler("link", link_command))
    application.add_handler(CommandHandler("attach", attach_command))
    application.add_handler(CommandHandler("detach", detach_command))
    application.add_handler(CommandHandler("list_attachments", list_attachments_command))
    application.add_handler(CommandHandler("list_all_attachments", list_all_attachments_command))
    application.add_handler(CommandHandler("attachment_stats", attachment_stats_command))
    
    
    # Register inline query handler
    application.add_handler(InlineQueryHandler(inlinequery, block=False))
    
    # Register callback query handler for attachment pagination
    application.add_handler(CallbackQueryHandler(handle_attachment_callbacks))
    
    # Set bot commands
    application.job_queue.run_once(lambda context: set_bot_commands(application), 0)
    
    logger.info("Uploader Bot is running...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()


import html
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError
from db import collection
from utils import clean_text
from .uploader import send_media, CHANNEL_ID  # is_valid_catbox_url removed
from db import is_uploader

logger = logging.getLogger(__name__)


async def attach_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_uploader(user_id):
        await update.message.reply_text("You are not authorized to use the upload command.")
        return

    if len(context.args) != 2:
        await update.message.reply_text(
            "Usage: /attach <character_id> <attached_character_id>\n"
            "Example: /attach 100 230\n"
            "This attaches character ID 100 to character ID 230."
        )
        return

    try:
        character_id = int(context.args[0])
        attached_character_id = int(context.args[1])

        if character_id == attached_character_id:
            await update.message.reply_text("Cannot attach a character to itself.")
            return

        character = await collection.find_one({"character_id": character_id})
        attached_character = await collection.find_one({"character_id": attached_character_id})

        if not character:
            await update.message.reply_text(f"Character ID {character_id} not found.")
            return
        if not attached_character:
            await update.message.reply_text(f"Character ID {attached_character_id} not found.")
            return

        # Only the first character must have 👾
        if character.get("event_emoji") != "👾":
            await update.message.reply_text(f"Character ID {character_id} does not have the required event emoji 👾.")
            return

        if (
            "attached_character_id" in character
            and character["attached_character_id"] == attached_character_id
        ):
            await update.message.reply_text(
                f"Character ID {character_id} is already attached to character ID {attached_character_id}."
            )
            return

        await collection.update_one(
            {"character_id": character_id},
            {"$set": {"attached_character_id": attached_character_id}},
        )

        # Build success message with details
        attached_char = await collection.find_one({"character_id": attached_character_id})
        attached_name = html.escape(attached_char["name"]) if attached_char else "Unknown"
        attached_anime = html.escape(attached_char.get("anime", "Unknown")) if attached_char else "Unknown"
        attached_rarity = html.escape(attached_char.get("rarity", "Unknown")) if attached_char else "Unknown"

        character_name = html.escape(character["name"])
        character_anime = html.escape(character["anime"])
        character_rarity = html.escape(character["rarity"])

        success_message = (
            f"<b>✅ Attachment Successful!</b>\n\n"
            f"<b>Attached Character:</b>\n"
            f"ID {character_id}: <b>{character_name}</b> [{character.get('event_emoji', '')}]\n"
            f"Anime: {character_anime}\n"
            f"Rarity: {character_rarity}\n\n"
            f"<b>Attached To:</b>\n"
            f"ID {attached_character_id}: <b>{attached_name}</b>\n"
            f"Anime: {attached_anime}\n"
            f"Rarity: {attached_rarity}\n\n"
            f"Attached by: <a href=\"tg://user?id={user_id}\">{html.escape(update.effective_user.first_name)}</a>"
        )

        await update.message.reply_text(success_message, parse_mode="HTML")

    except ValueError:
        await update.message.reply_text("Character IDs must be numbers.")
    except Exception as e:
        logger.error(f"Attach failed: {e}")
        await update.message.reply_text("An error occurred while attaching. Please try again.")


async def detach_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_uploader(user_id):
        await update.message.reply_text("You are not authorized to use the upload command.")
        return

    if len(context.args) != 2:
        await update.message.reply_text(
            "Usage: /detach <character_id> <attached_character_id>\n"
            "Example: /detach 100 230\n"
            "This detaches character ID 230 from character ID 100."
        )
        return

    try:
        character_id = int(context.args[0])
        attached_character_id = int(context.args[1])

        character = await collection.find_one({"character_id": character_id})
        if not character:
            await update.message.reply_text(f"Character ID {character_id} not found.")
            return

        if character.get("event_emoji") != "👾":
            await update.message.reply_text(f"Character ID {character_id} does not have the required event emoji 👾.")
            return

        if (
            "attached_character_id" not in character
            or character["attached_character_id"] != attached_character_id
        ):
            await update.message.reply_text(
                f"Character ID {attached_character_id} is not attached to character ID {character_id}."
            )
            return

        await collection.update_one(
            {"character_id": character_id},
            {"$unset": {"attached_character_id": ""}},
        )

        character_name = html.escape(character["name"])
        character_anime = html.escape(character["anime"])
        character_rarity = html.escape(character["rarity"])

        success_message = (
            f"<b>✅ Detachment Successful!</b>\n\n"
            f"<b>Detached Character:</b>\n"
            f"ID {character_id}: <b>{character_name}</b> [{character.get('event_emoji', '')}]\n"
            f"Anime: {character_anime}\n"
            f"Rarity: {character_rarity}\n\n"
            f"<b>Previously Attached To:</b>\n"
            f"ID {attached_character_id}\n\n"
            f"Detached by: <a href=\"tg://user?id={user_id}\">{html.escape(update.effective_user.first_name)}</a>"
        )

        await update.message.reply_text(success_message, parse_mode="HTML")

    except ValueError:
        await update.message.reply_text("Character IDs must be numbers.")
    except Exception as e:
        logger.error(f"Detach failed: {e}")
        await update.message.reply_text("An error occurred while detaching. Please try again.")


async def list_attachments_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text(
            "Usage: /list_attachments <character_id>\n"
            "Example: /list_attachments 100"
        )
        return

    try:
        character_id = int(context.args[0])
        character = await collection.find_one({"character_id": character_id})
        if not character:
            await update.message.reply_text(f"Character ID {character_id} not found.")
            return

        if character.get("event_emoji") != "👾":
            await update.message.reply_text(f"Character ID {character_id} does not have the required event emoji 👾.")
            return

        if "attached_character_id" not in character:
            await update.message.reply_text(
                f"Character ID {character_id} ({character['name']}) has no attachment."
            )
            return

        attached_char = await collection.find_one({"character_id": character["attached_character_id"]})
        if not attached_char:
            await update.message.reply_text(
                f"Attached character ID {character['attached_character_id']} not found."
            )
            return

        attached_name = html.escape(attached_char["name"])
        message = (
            f"<b>Attachment for Character ID {character_id} ({html.escape(character['name'])}):</b>\n"
            f"{character['attached_character_id']}: {attached_name}"
        )
        await update.message.reply_text(message, parse_mode="HTML")

    except ValueError:
        await update.message.reply_text("Character ID must be a number.")
    except Exception as e:
        logger.error(f"List attachments failed: {e}")
        await update.message.reply_text("An error occurred while listing attachments.")


async def list_all_attachments_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        page = 1
        if len(context.args) == 1:
            page = int(context.args[0])
            if page < 1:
                await update.message.reply_text("Page number must be 1 or greater.")
                return
        elif len(context.args) > 1:
            await update.message.reply_text(
                "Usage: /list_all_attachments [page_number]\n"
                "Example: /list_all_attachments 2"
            )
            return

        await _send_attachments_page(update, context, page)

    except ValueError:
        await update.message.reply_text("Page number must be a valid number.")
    except Exception as e:
        logger.error(f"List all attachments failed: {e}")
        await update.message.reply_text("An error occurred while listing all attachments. Please try again.")


async def _send_attachments_page(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int):
    try:
        attached_characters = collection.find({
            "attached_character_id": {"$exists": True},
            "event_emoji": "👾",
        })

        attached_list = []
        async for character in attached_characters:
            attached_list.append(character)

        attached_list.sort(key=lambda x: x["character_id"])

        if not attached_list:
            await update.message.reply_text("No character attachments found with the required event emoji 👾.")
            return

        items_per_page = 15
        total_items = len(attached_list)
        total_pages = (total_items + items_per_page - 1) // items_per_page

        if page > total_pages:
            await update.message.reply_text(f"Page {page} doesn't exist. Total pages: {total_pages}")
            return

        start_idx = (page - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, total_items)

        message_parts = [
            f"<b>All Character Attachments with 👾 (Page {page}/{total_pages})</b>",
            f"Total Attachments: {total_items}\n",
        ]

        for i in range(start_idx, end_idx):
            character = attached_list[i]
            character_id = character["character_id"]
            character_name = html.escape(character["name"])
            character_anime = html.escape(character.get("anime", "Unknown"))
            character_rarity = html.escape(character.get("rarity", "Unknown"))
            attached_id = character["attached_character_id"]

            attached_char = await collection.find_one({"character_id": attached_id})
            if attached_char:
                attached_name = html.escape(attached_char["name"])
                attached_anime = html.escape(attached_char.get("anime", "Unknown"))
                attached_rarity = html.escape(attached_char.get("rarity", "Unknown"))
            else:
                attached_name = "Not Found"
                attached_anime = "Unknown"
                attached_rarity = "Unknown"

            attachment_info = (
                f"<b>{i + 1}.</b> ID {character_id}: <b>{character_name}</b> ({character_rarity})\n"
                f"   Anime: {character_anime}\n"
                f"   Attached to ID {attached_id}: <b>{attached_name}</b> ({attached_rarity})\n"
                f"   Anime: {attached_anime}\n"
            )
            message_parts.append(attachment_info)

        message = "\n".join(message_parts)

        keyboard = []
        nav_buttons = []

        if page > 1:
            nav_buttons.append(InlineKeyboardButton("First", callback_data="attachments_page_1"))
            nav_buttons.append(InlineKeyboardButton("Previous", callback_data=f"attachments_page_{page-1}"))

        nav_buttons.append(
            InlineKeyboardButton(f"Page {page}/{total_pages}", callback_data="attachments_current")
        )

        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton("Next", callback_data=f"attachments_page_{page+1}"))
            nav_buttons.append(InlineKeyboardButton("Last", callback_data=f"attachments_page_{total_pages}"))

        for i in range(0, len(nav_buttons), 3):
            keyboard.append(nav_buttons[i : i + 3])

        utility_buttons = [
            InlineKeyboardButton("Refresh", callback_data=f"attachments_page_{page}"),
            InlineKeyboardButton("Stats", callback_data="attachment_stats"),
        ]
        keyboard.append(utility_buttons)

        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.callback_query:
            try:
                await update.callback_query.edit_message_text(
                    text=message,
                    parse_mode="HTML",
                    reply_markup=reply_markup,
                )
                await update.callback_query.answer()
            except Exception:
                await update.callback_query.message.reply_text(
                    text=message,
                    parse_mode="HTML",
                    reply_markup=reply_markup,
                )
                await update.callback_query.answer("Updated!")
        else:
            await update.message.reply_text(
                text=message,
                parse_mode="HTML",
                reply_markup=reply_markup,
            )

    except Exception as e:
        logger.error(f"Send attachments page failed: {e}")
        error_msg = "An error occurred while loading attachments page."

        if update.callback_query:
            await update.callback_query.answer(error_msg)
        else:
            await update.message.reply_text(error_msg)


async def attachment_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        total_attached = await collection.count_documents({
            "attached_character_id": {"$exists": True},
            "event_emoji": "👾",
        })

        total_characters = await collection.count_documents({})

        attachment_rate = (total_attached / total_characters * 100) if total_characters > 0 else 0.0

        pipeline = [
            {
                "$match": {
                    "attached_character_id": {"$exists": True},
                    "event_emoji": "👾",
                }
            },
            {
                "$group": {
                    "_id": "$anime",
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"count": -1}},
            {"$limit": 10},
        ]

        top_anime_attachments = []
        async for doc in collection.aggregate(pipeline):
            anime_name = html.escape(doc["_id"]) if doc["_id"] else "Unknown"
            top_anime_attachments.append(f"• {anime_name}: {doc['count']} attachments")

        message_parts = [
            "<b>Character Attachment Statistics (👾 Only)</b>\n",
            f"Total Attached Characters with 👾: <b>{total_attached}</b>",
            f"Total Characters: <b>{total_characters}</b>",
            f"Attachment Rate (👾 only): <b>{attachment_rate:.1f}%</b>\n",
        ]

        if top_anime_attachments:
            message_parts.append("<b>Top 10 Anime by Attachments (👾 only):</b>")
            message_parts.extend(top_anime_attachments)

        message = "\n".join(message_parts)

        keyboard = []
        if update.callback_query:
            keyboard.append(
                [InlineKeyboardButton("Back to List", callback_data="attachments_page_1")]
            )

        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

        if update.callback_query:
            try:
                await update.callback_query.edit_message_text(
                    text=message,
                    parse_mode="HTML",
                    reply_markup=reply_markup,
                )
                await update.callback_query.answer()
            except Exception:
                await update.callback_query.message.reply_text(
                    message, parse_mode="HTML", reply_markup=reply_markup
                )
                await update.callback_query.answer("Stats loaded!")
        else:
            await update.message.reply_text(message, parse_mode="HTML", reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Attachment stats failed: {e}")
        error_msg = "An error occurred while getting attachment statistics."

        if update.callback_query:
            await update.callback_query.answer(error_msg)
        else:
            await update.message.reply_text(error_msg)


async def handle_attachment_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query.data.startswith("attachments_page_"):
        try:
            page = int(query.data.split("_")[-1])
            await _send_attachments_page(update, context, page)
        except (ValueError, IndexError):
            await query.answer("Invalid page number")

    elif query.data == "attachment_stats":
        await attachment_stats_command(update, context)

    elif query.data == "attachments_current":
        await query.answer("You're viewing the current page")

    else:
        await query.answer("Unknown command")
        

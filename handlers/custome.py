import re
import html
import logging
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError
from db import collection, get_next_character_id, is_uploader, user_collection
from utils import clean_text
from config import EVENT_MAPPING as event_mapping
from config import SUDO_USERS

logger = logging.getLogger(__name__)

IMGBB_API_KEY = "29660d38fea001b1ae4dab1f35c605a6"
CHANNEL_ID = -1002594115750

def is_valid_url(url: str) -> bool:
    url_pattern = r'^https://[^\s/$.?#].[^\s]*$'
    try:
        return bool(re.match(url_pattern, url))
    except Exception:
        return False

def escape_html(text: str) -> str:
    return html.escape(text)

async def send_media(bot, chat_id, media_url, caption, parse_mode):
    try:
        if media_url.lower().endswith(".mp4"):
            return await bot.send_video(
                chat_id=chat_id,
                video=media_url,
                caption=caption,
                parse_mode=parse_mode
            )
        else:
            return await bot.send_photo(
                chat_id=chat_id,
                photo=media_url,
                caption=caption,
                parse_mode=parse_mode
            )
    except TelegramError as e:
        logger.error(f"Failed to send media: {e}")
        raise

async def custome_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in SUDO_USERS:
        await update.message.reply_text("❌ You are not authorized to use the /custome command.")
        return

    if len(context.args) < 5:
        await update.message.reply_text(
            "ℹ️ Usage:\n/custome <img-link> <[event-emoji]character-name> <anime-name> <rarity> <user-id>\n"
            "Example:\n/custome https://img.link [🎃]Kurumi-Tokisaki Date-A-Live Mythic 1234567890\n"
            "Or:\n/custome@TakeUploaderBot https://i.ibb.co/kgzyrw4g/image.jpg hinata-hyuga Naruto/Boruto 🥋Karate 6857856691"
        )
        return

    img_link, raw_name, anime_name, rarity, custome_user_id = context.args[:5]

    if not is_valid_url(img_link):
        await update.message.reply_text("⚠️ Invalid image URL. Please provide a valid HTTPS link.")
        return

    try:
        custome_user_id = int(custome_user_id)
    except ValueError:
        await update.message.reply_text("⚠️ Invalid user ID. Please provide a valid numeric user ID.")
        return

    match = re.match(r"\[(.*?)\](.+)", raw_name)
    if match:
        event_emoji, name = match.groups()
    else:
        event_emoji = "-"
        name = raw_name

    name = clean_text(name.replace("-", " ")).title()
    anime_name = clean_text(anime_name.replace("-", " ")).title()
    rarity = clean_text(rarity.replace("-", " ")).title()

    if not rarity:
        await update.message.reply_text("⚠️ Rarity cannot be empty.")
        return

    character_id = await get_next_character_id()
    
    if character_id % 2 != 0:
        existing_character = await collection.find_one({
            "name": name,
            "anime": anime_name,
            "is_custom": True
        })
        
        if existing_character:
            await update.message.reply_text(
                f"⚠️ A custom character with name '{name}' from '{anime_name}' already exists (ID: {existing_character['character_id']}).\n"
                "Use /custome_update to modify it or try again with different details."
            )
            return

    character_data = {
        "character_id": character_id,
        "image": img_link,
        "name": name,
        "anime": anime_name,
        "rarity": rarity,
        "custome": custome_user_id,  # Storing user ID instead of costume name
        "uploader_id": user_id,
        "uploader_name": update.effective_user.first_name,
        "is_custom": True
    }

    if event_emoji != "-" and event_emoji in event_mapping:
        character_data["event"] = event_mapping[event_emoji]
        character_data["event_emoji"] = event_emoji

    escaped_name = escape_html(name)
    escaped_anime = escape_html(anime_name)
    escaped_rarity = escape_html(rarity)
    escaped_event = escape_html(event_mapping[event_emoji]) if event_emoji != "-" and event_emoji in event_mapping else None
    escaped_uploader = escape_html(update.effective_user.first_name)

    message_parts = [
        "<b>OwO! Check out this Custom Character!</b>\n",
        f"<b>{escaped_anime}</b>",
        f"🆔️{character_data['character_id']}: {escaped_name}" + (f" [{event_emoji}]" if "event_emoji" in character_data else ""),
        f"(𝙍𝘼𝙍𝙄𝙏𝙔: {escaped_rarity})\n",
        f"👤 𝘾𝙪𝙨𝙩𝙤𝙢𝙚 𝙛𝙤𝙧: <a href=\"tg://user?id={custome_user_id}\">user</a>"
    ]

    if escaped_event:
        message_parts.append(f"<b>{escaped_event}\n</b>")

    message_parts.append(f"➼ ᴀᴅᴅᴇᴅ ʙʏ: <a href=\"tg://user?id={user_id}\">{escaped_uploader}</a>")
    message = "\n".join(message_parts)

    try:
        sent_message = await send_media(context.bot, CHANNEL_ID, img_link, message, "HTML")
        character_data["channel_message_id"] = sent_message.message_id

        # Insert character data
        await collection.insert_one(character_data)
        
        # Update user's collection with the new character
        await user_collection.update_one(
            {"user_id": custome_user_id},
            {
                "$inc": {f"characters.{character_id}": 1},
                "$setOnInsert": {
                    "first_name": "Unknown",  # Will be updated when user interacts
                    "username": "unknown"     # Will be updated when user interacts
                }
            },
            upsert=True
        )

        post_link = f"https://t.me/c/{str(CHANNEL_ID)[4:]}/{sent_message.message_id}"
        keyboard = [[InlineKeyboardButton("View Post", url=post_link)]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"✅ Custom character '{name}' (ID: {character_data['character_id']}) from '{anime_name}' "
            f"with rarity {rarity} for user {custome_user_id} "
            f"{'and event ' + event_mapping[event_emoji] if event_emoji != '-' and event_emoji in event_mapping else ''} "
            f"uploaded successfully!",
            reply_markup=reply_markup
        )

    except Exception as e:
        logger.error(f"Custom upload failed: {e}")
        await update.message.reply_text("⚠️ An error occurred while uploading the custom character. Please try again.")

async def custome_update_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in SUDO_USERS:
        await update.message.reply_text("❌ You are not authorized to use the /custome_update command.")
        return

    if len(context.args) < 3:
        await update.message.reply_text("ℹ️ Usage:\n/custome_update <id> <field> <new_value>\n"
                                       "Fields: name, anime, rarity, img, event, custome\n"
                                       "Example:\n/custome_update 123 rarity Ultra-Mythic\n"
                                       "To update user: /custome_update 123 custome 9876543210")
        return

    try:
        character_id = int(context.args[0])
        field = context.args[1].lower()
        new_value = " ".join(context.args[2:])

        if field not in ["name", "anime", "rarity", "img", "event", "custome"]:
            await update.message.reply_text("⚠️ Invalid field. Use: name, anime, rarity, img, event, custome")
            return

        character = await collection.find_one({"character_id": character_id, "is_custom": True})
        if not character:
            await update.message.reply_text("❌ Custom character not found or not a custom character.")
            return

        update_data = {}
        unset_data = {}

        if field == "img":
            if not is_valid_url(new_value):
                await update.message.reply_text("⚠️ Invalid image URL. Please provide a valid HTTPS link.")
                return
            update_data["image"] = new_value

        elif field == "event":
            if new_value == "-":
                unset_data = {"event": "", "event_emoji": ""}
            elif new_value in event_mapping:
                update_data["event"] = event_mapping[new_value]
                update_data["event_emoji"] = new_value
            else:
                await update.message.reply_text(f"⚠️ Invalid event emoji. Valid: {list(event_mapping.keys())} or '-' to remove.")
                return
        elif field == "custome":
            try:
                new_user_id = int(new_value)
                old_user_id = character.get("custome")
                
                # Remove from old user's collection
                if old_user_id:
                    await user_collection.update_one(
                        {"user_id": old_user_id},
                        {"$unset": {f"characters.{character_id}": ""}}
                    )
                
                # Add to new user's collection
                await user_collection.update_one(
                    {"user_id": new_user_id},
                    {
                        "$inc": {f"characters.{character_id}": 1},
                        "$setOnInsert": {
                            "first_name": "Unknown",
                            "username": "unknown"
                        }
                    },
                    upsert=True
                )
                update_data["custome"] = new_user_id
            except ValueError:
                await update.message.reply_text("⚠️ Invalid user ID. Please provide a valid numeric user ID.")
                return
        else:
            update_data[field] = clean_text(new_value).title()
            if field == "rarity" and not update_data[field]:
                await update.message.reply_text("⚠️ Rarity cannot be empty.")
                return

        updated_character = {**character, **update_data}
        for key in unset_data:
            updated_character.pop(key, None)

        if "channel_message_id" in character:
            try:
                await context.bot.delete_message(chat_id=CHANNEL_ID, message_id=character["channel_message_id"])
            except Exception as e:
                logger.warning(f"Could not delete old post (ID: {character['channel_message_id']}): {e}. Proceeding with new post.")

        name_line = escape_html(updated_character["name"])
        if "event_emoji" in updated_character:
            name_line += f" [{updated_character['event_emoji']}]"

        message_parts = [
            "<b>OwO! Check out this Updated Custom Character!</b>\n",
            f"<b>{escape_html(updated_character['anime'])}</b>",
            f"🆔️{character_id}: {name_line}",
            f"(𝙍𝘼𝙍𝙄𝙏𝙔: {escape_html(updated_character['rarity'])})\n",
            f"👤 𝘾𝙪𝙨𝙩𝙤𝙢𝙚: <a href=\"tg://user?id={updated_character['custome']}\">user</a>"
        ]

        if "event" in updated_character:
            message_parts.append(f"<b>{escape_html(updated_character['event'])}\n</b>")

        message_parts.append(f"➼ ᴜᴘᴅᴀᴛᴇᴅ ʙʏ: <a href=\"tg://user?id={user_id}\">{escape_html(update.effective_user.first_name)}</a>")
        message = "\n".join(message_parts)

        sent = await send_media(context.bot, CHANNEL_ID, updated_character["image"], message, "HTML")

        update_query = {"$set": {**update_data, "channel_message_id": sent.message_id}}
        if unset_data:
            update_query["$unset"] = unset_data

        await collection.update_one({"character_id": character_id}, update_query)

        post_link = f"https://t.me/c/{str(CHANNEL_ID)[4:]}/{sent.message_id}"
        keyboard = [[InlineKeyboardButton("View Post", url=post_link)]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"✅ Custom character {character_id} updated and reposted successfully!",
            reply_markup=reply_markup
        )

    except Exception as e:
        logger.error(f"Custom update failed: {e}")
        await update.message.reply_text("⚠️ An error occurred while updating the custom character. Please try again.")

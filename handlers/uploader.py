import re
import html
import logging
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import RetryAfter, TelegramError
from db import collection, get_next_character_id, is_uploader
from utils import clean_text
from config import RARITY_MAPPING as rarity_mapping
from config import EVENT_MAPPING as event_mapping

logger = logging.getLogger(__name__)

IMGBB_API_KEY = "29660d38fea001b1ae4dab1f35c605a6"
CHANNEL_ID = -1004341552881  # Updated Channel ID

def escape_html(text: str) -> str:
    return html.escape(text)

async def send_media(bot, chat_id, media_url, caption, parse_mode):
    try:
        if media_url.lower().endswith((".mp4", ".webm")):
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

async def upload_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_uploader(user_id):
        await update.message.reply_text("❌ You are not authorized to use the upload command.")
        return

    if len(context.args) < 4:
        await update.message.reply_text(
            "ℹ️ Usage:\n/upload <image-link> <[event-emoji]character-name> <anime-name> <rarity> [custome] [price]\n\n"
            "Example:\n/upload https://example.com/image.jpg [🎃]Kurumi-Tokisaki Date-A-Live 4 Halloween\n\n"
            "Example with price:\n/upload https://imgur.com/abc123.jpg Kurumi-Tokisaki Date-A-Live 4 - - 50\n\n"
            "✅ Any image/video link accepted!"
        )
        return

    img_link, raw_name, anime_name, rarity = context.args[:4]
    custome = None
    price = None

    # ✅ REMOVED Catbox validation - ALL links accepted now
    # Just basic URL check
    if not (img_link.startswith(('http://', 'https://'))):
        await update.message.reply_text(
            "⚠️ Please provide a valid HTTP/HTTPS link."
        )
        return

    # Parse optional fields
    if len(context.args) > 4:
        remaining_args = context.args[4:]
        # Check if next arg is custome (not a number) or price (number)
        if remaining_args[0].isdigit():
            price = int(remaining_args[0])
        else:
            custome = clean_text(remaining_args[0]).title()
            if len(remaining_args) > 1 and remaining_args[1].isdigit():
                price = int(remaining_args[1])

    match = re.match(r"\[(.*?)\](.+)", raw_name)
    if match:
        event_emoji, name = match.groups()
    else:
        event_emoji = "-"
        name = raw_name

    name = clean_text(name.replace("-", " ")).title()
    anime_name = clean_text(anime_name.replace("-", " ")).title()

    try:
        rarity = int(rarity)
        if rarity not in rarity_mapping:
            await update.message.reply_text(f"⚠️ Invalid rarity. Valid options: {list(rarity_mapping.keys())}")
            return
    except ValueError:
        await update.message.reply_text("⚠️ Rarity must be a number.")
        return

    # Generate character_id based on rarity
    if rarity == 11:
        candidate_id = 100000
        while await collection.find_one({"character_id": candidate_id}):
            candidate_id += 1
        character_id = candidate_id
    else:
        character_id = await get_next_character_id()

    character_data = {
        "character_id": character_id,
        "image": img_link,
        "name": name,
        "anime": anime_name,
        "rarity": rarity_mapping[rarity],
        "uploader_id": user_id,
        "uploader_name": update.effective_user.first_name
    }

    if custome:
        character_data["custome"] = custome
        
    if price is not None:
        character_data["price"] = price

    if event_emoji != "-" and event_emoji in event_mapping:
        character_data["event"] = event_mapping[event_emoji]
        character_data["event_emoji"] = event_emoji

    escaped_name = escape_html(name)
    escaped_anime = escape_html(anime_name)
    escaped_rarity = escape_html(rarity_mapping[rarity])
    escaped_event = escape_html(event_mapping[event_emoji]) if event_emoji != "-" and event_emoji in event_mapping else None
    escaped_uploader = escape_html(update.effective_user.first_name)
    escaped_price = escape_html(f"Æ: {price}") if price is not None else ""

    message_parts = [
        "<b>OwO! Check out this Character!</b>\n",
        f"<b>{escaped_anime}</b>",
        f"🆔️{character_data['character_id']}: {escaped_name}" + (f" [{event_emoji}]" if "event_emoji" in character_data else ""),
        f"(𝙍𝘼𝙍𝙄𝙏𝙔: {escaped_rarity})\n"
    ]

    if "custome" in character_data:
        message_parts.append(f"🧥 𝘾𝙪𝙨𝙩𝙤𝙢𝙚: {escape_html(character_data['custome'])}")

    if escaped_price:
        message_parts.append(escaped_price)

    if escaped_event:
        message_parts.append(f"<b>{escaped_event}\n</b>")

    message_parts.append(f"➼ ᴀᴅᴅᴇᴅ ʙʏ: <a href=\"tg://user?id={user_id}\">{escaped_uploader}</a>")
    message = "\n".join(message_parts)

    try:
        sent_message = await send_media(context.bot, CHANNEL_ID, img_link, message, "HTML")
        character_data["channel_message_id"] = sent_message.message_id

        await collection.insert_one(character_data)

        post_link = f"https://t.me/c/{str(CHANNEL_ID)[4:]}/{sent_message.message_id}"
        keyboard = [[InlineKeyboardButton("View Post", url=post_link)]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        response_text = (
            f"✅ Character '{name}' (ID: {character_data['character_id']}) from '{anime_name}' with rarity {rarity_mapping[rarity]} "
            f"{'and event ' + event_mapping[event_emoji] if event_emoji != '-' and event_emoji in event_mapping else ''} "
            f"{'and custome ' + character_data['custome'] if 'custome' in character_data else ''} "
            f"{'and price ' + str(price) if price is not None else ''} uploaded successfully!"
        )

        await update.message.reply_text(
            response_text,
            reply_markup=reply_markup
        )

    except Exception as e:
        logger.error(f"Upload failed: {e}")
        await update.message.reply_text("⚠️ An error occurred while uploading. Please try again.")

async def update_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_uploader(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized.")
        return

    if len(context.args) < 3:
        await update.message.reply_text("Usage: /update <id> <field> <new_value>\nFields: name, anime, rarity, img, event, price, custome")
        return

    try:
        character_id = int(context.args[0])
        field = context.args[1].lower()
        new_value = " ".join(context.args[2:])

        if field not in ["name", "anime", "rarity", "img", "event", "price", "custome"]:
            await update.message.reply_text("Invalid field. Use: name, anime, rarity, img, event, price, custome")
            return

        character = await collection.find_one({"character_id": character_id})
        if not character:
            await update.message.reply_text("❌ Character not found.")
            return

        update_data = {}
        unset_data = {}

        if field == "img":
            # ✅ REMOVED Catbox validation - ALL links accepted now
            if not new_value.startswith(('http://', 'https://')):
                await update.message.reply_text(
                    "⚠️ Please provide a valid HTTP/HTTPS link."
                )
                return
            update_data["image"] = new_value

        elif field == "rarity":
            rarity = int(new_value)
            if rarity not in rarity_mapping:
                await update.message.reply_text(f"Invalid rarity. Use: {list(rarity_mapping.keys())}")
                return
            update_data["rarity"] = rarity_mapping[rarity]

        elif field == "event":
            if new_value == "-":
                unset_data = {"event": "", "event_emoji": ""}
            elif new_value in event_mapping:
                update_data["event"] = event_mapping[new_value]
                update_data["event_emoji"] = new_value
            else:
                await update.message.reply_text(f"Invalid event emoji. Valid: {list(event_mapping.keys())} or '-' to remove.")
                return
                
        elif field == "price":
            if new_value == "-":
                unset_data = {"price": ""}
            else:
                try:
                    update_data["price"] = int(new_value)
                except ValueError:
                    await update.message.reply_text("Price must be a number or '-' to remove.")
                    return
                    
        elif field == "custome":
            if new_value == "-":
                unset_data = {"custome": ""}
            else:
                update_data["custome"] = clean_text(new_value).title()
        else:
            update_data[field] = clean_text(new_value).title()

        updated_character = {**character, **update_data}
        for key in unset_data:
            updated_character.pop(key, None)

        # Delete old post if exists, ignore error if it fails
        if "channel_message_id" in character:
            try:
                await context.bot.delete_message(chat_id=CHANNEL_ID, message_id=character["channel_message_id"])
            except Exception as e:
                logger.warning(f"Could not delete old post (ID: {character['channel_message_id']}): {e}. Proceeding with new post.")

        name_line = escape_html(updated_character["name"])
        if "event_emoji" in updated_character:
            name_line += f" [{updated_character['event_emoji']}]"

        message_parts = [
            "<b>OwO! Check out this Update!</b>\n",
            f"<b>{escape_html(updated_character['anime'])}</b>",
            f"🆔️{character_id}: {name_line}",
            f"(𝙍𝘼𝙍𝙄𝙏𝙔: {escape_html(updated_character['rarity'])})\n"
        ]

        if "custome" in updated_character:
            message_parts.append(f"🧥 𝘾𝙪𝙨𝙩𝙤𝙢𝙚: {escape_html(updated_character['custome'])}")

        if "price" in updated_character:
            message_parts.append(f"Æ: {escape_html(str(updated_character['price']))}")

        if "event" in updated_character:
            message_parts.append(f"<b>{escape_html(updated_character['event'])}\n</b>")

        message_parts.append(f"➼ ᴜᴘᴅᴀᴛᴇᴅ ʙʏ: <a href=\"tg://user?id={update.effective_user.id}\">{escape_html(update.effective_user.first_name)}</a>")
        message = "\n".join(message_parts)

        sent = await send_media(context.bot, CHANNEL_ID, updated_character["image"], message, "HTML")

        update_query = {"$set": {**update_data, "channel_message_id": sent.message_id}}
        if unset_data:
            update_query["$unset"] = unset_data

        await collection.update_one({"character_id": character_id}, update_query)

        await update.message.reply_text(f"✅ Character {character_id} updated and reposted.")

    except Exception as e:
        logger.error(f"Update failed: {e}")
        await update.message.reply_text("⚠️ Update failed.")
            

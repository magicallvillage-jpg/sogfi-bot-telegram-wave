import re
import time
from html import escape
from cachetools import TTLCache
from telegram import InlineQueryResultPhoto, InlineQueryResultVideo, Update
from telegram.ext import InlineQueryHandler, CallbackContext
from db import collection
from config import EVENT_MAPPING  # Import event emoji mapping

# Cache setup
all_characters_cache = TTLCache(maxsize=10000, ttl=36000)

async def inlinequery(update: Update, context: CallbackContext) -> None:
    query = update.inline_query.query.strip()
    offset = int(update.inline_query.offset) if update.inline_query.offset else 0

    # Search characters based on query
    if query:
        regex = re.compile(query, re.IGNORECASE)
        all_characters = await collection.find({
            "$or": [{"name": regex}, {"anime": regex}]
        }).to_list(length=None)
    else:
        all_characters = all_characters_cache.get("all_characters")
        if not all_characters:
            all_characters = await collection.find({}).to_list(length=None)
            all_characters_cache["all_characters"] = all_characters

    characters = all_characters[offset:offset + 50]
    next_offset = str(offset + 50) if len(all_characters) > offset + 50 else ""

    results = []
    for char in characters:
        # Extract the emoji key from the full event string
        emoji = ""
        if "event" in char and char["event"]:
            for key_emoji, full_event in EVENT_MAPPING.items():
                if char["event"] == full_event:
                    emoji = f" [{key_emoji}]"
                    break

        # Build caption
        caption = (
            "OwO! Check out this waifu!\n\n"
            f"<b>{escape(char['anime'])}</b>\n"
            f"<b>{char['character_id']} {escape(char['name'])}{emoji}</b>\n"
        )

        caption += f"(𝙍𝘼𝙍𝙄𝙏𝙔: {escape(char['rarity'])})\n"

        if "event" in char and char["event"]:
            caption += f"{escape(char['event'])}\n"

        caption += (
            f"\n<b>Uploaded by <a href='tg://user?id={char['uploader_id']}'>{escape(char['uploader_name'])}</a></b>"
        )

        ext = char['image'].split('.')[-1].lower()
        title = f"{char['name']} - {char['anime']}"
        result_id = f"{char['character_id']}_{time.time()}"

        if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
            results.append(
                InlineQueryResultPhoto(
                    id=result_id,
                    photo_url=char['image'],
                    thumbnail_url=char['image'],
                    caption=caption,
                    title=title,
                    parse_mode='HTML'
                )
            )
        elif ext in ['mp4', 'webm', 'mov', 'avi']:
            results.append(
                InlineQueryResultVideo(
                    id=result_id,
                    video_url=char['image'],
                    mime_type='video/mp4',
                    thumbnail_url=char['image'],
                    title=title,
                    caption=caption,
                    parse_mode='HTML'
                )
            )

    await update.inline_query.answer(results, next_offset=next_offset, cache_time=5)

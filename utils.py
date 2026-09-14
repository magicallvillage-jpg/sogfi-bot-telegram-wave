# utils.py

from config import RARITY_MAPPING, EVENT_MAPPING, CHANNEL_USERNAME

def title_case(text: str) -> str:
    return text.strip().title()

# Utility function for cleaning text
def clean_text(text: str) -> str:
    """Cleans and formats the input text."""
    return " ".join(text.split()).strip().title()



def format_character_message(character: dict, updated_by: str = None, updated_fields: list = None) -> str:
    name = title_case(character["name"])
    anime = title_case(character["anime"])
    rarity = RARITY_MAPPING.get(character["rarity"], "❓ Unknown")
    event = EVENT_MAPPING.get(character.get("event", ""), "")
    
    lines = [
        f"*{name}*",
        f"_{anime}_",
        "",
        f"{rarity}"
    ]

    if event:
        lines.append(f"{event}")
    
    if updated_by and updated_fields:
        lines.append("")
        lines.append(f"*Updated by* {updated_by}")
        lines.append(f"*Changed:* {', '.join(updated_fields)}")
    
    return "\n".join(lines)

def parse_update_args(args: str) -> dict:
    """Parses args string from /update and returns a dict of updates."""
    updates = {}
    for part in args.split(";"):
        if "=" in part:
            key, value = part.split("=", 1)
            updates[key.strip().lower()] = value.strip()
    return updates

def get_updated_fields(original: dict, updated: dict) -> list:
    """Returns a list of fields that were changed."""
    changed = []
    for key in updated:
        if key in original and original[key] != updated[key]:
            changed.append(key)
    return changed

def generate_channel_link(message_id: int) -> str:
    return f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}/{message_id}"

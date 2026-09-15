import os
import logging
from typing import Optional

import certifi
import motor.motor_asyncio
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MONGO_URL = os.getenv("MONGO_URL")
if not MONGO_URL:
    raise RuntimeError(
        "MONGO_URL is not set. Add it to a .env file next to main.py."
    )

client = motor.motor_asyncio.AsyncIOMotorClient(
    MONGO_URL,
    tlsCAFile=certifi.where(),
)

# ---------------------------------------------------------------------------
# Databases
# ---------------------------------------------------------------------------
db = client["Neww"]
characters_db = client["Cluster0"]  # shared character catalog (also read by the main bot)

# ---------------------------------------------------------------------------
# Collections
# ---------------------------------------------------------------------------
collection = characters_db["Takecharacters4"]  # shared character catalog (this bot writes to it)
uploader_collection = db["uploaders"]
group_settings = db["group_collections"]
group_collection = db["lmao000o"]
user_collection = db["userrs"]
daily_limit_collection = db["dailly"]
banned_users_collection = db["ban"]


# ---------------------------------------------------------------------------
# Character ID allocation
# ---------------------------------------------------------------------------
async def get_next_character_id() -> int:
    """
    Get the next available character ID.

    IDs >= 100000 are reserved for "custom" (rarity 11 / one-off) characters
    created via /custome, so normal uploads only look at IDs below that range.
    """
    last_character = await collection.find_one(
        {"character_id": {"$lt": 100000}},
        sort=[("character_id", -1)],
    )
    return last_character["character_id"] + 1 if last_character else 1


# ---------------------------------------------------------------------------
# Uploader management
# ---------------------------------------------------------------------------
async def is_uploader(user_id: int) -> bool:
    """Check if the user is an authorized uploader."""
    uploader = await uploader_collection.find_one({"user_id": user_id})
    return uploader is not None


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
async def ensure_indexes() -> None:
    """Create/verify indexes. Call once during application startup."""
    await collection.create_index([("character_id", 1)], unique=True, sparse=True)
    await uploader_collection.create_index([("user_id", 1)], unique=True, sparse=True)
    await user_collection.create_index([("user_id", 1)], unique=True, sparse=True)
    logger.info("Indexes created/verified")

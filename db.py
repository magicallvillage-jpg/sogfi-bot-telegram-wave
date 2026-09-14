import motor.motor_asyncio
from config import MONGO_URL



client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
db = client["Neww"]
db2 = client["Cluster0"]

# Collections
collection = db2["Takecharacters4"]  # Main characters collection
uploader_collection = db["uploaders"]
counter_collection = db["counters"]
group_settings = db["group_collections"]
group_collection = db["lmao000o"]
user_collection = db["userrs"]
daily_limit_collection = db["dailly"]
banned_users_collection = db["ban"]



async def get_next_character_id() -> int:
    # Find the last character with ID < 100000
    last_character = await collection.find_one(
        {"character_id": {"$lt": 100000}}, 
        sort=[("character_id", -1)]
    )
    return last_character["character_id"] + 1 if last_character else 1
    
async def is_uploader(user_id: int) -> bool:
    """
    Check if the user is an authorized uploader.
    """
    uploader = await uploader_collection.find_one({"user_id": user_id})
    return uploader is not None

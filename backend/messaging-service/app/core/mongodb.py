import logging
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings

logger = logging.getLogger(__name__)


class MongoClient:
    def __init__(self):
        self.client = None
        self.db = None

    async def connect(self):
        self.client = AsyncIOMotorClient(settings.MONGODB_URL)
        self.db = self.client[settings.MONGODB_DB_NAME]
        await self._init_collections()
        logger.info("MongoDB connection established")

    async def _init_collections(self):
        conversations = self.db.conversations
        await conversations.create_index("conversation_id", unique=True)
        await conversations.create_index("participants")
        await conversations.create_index("updated_at")
        await conversations.create_index(
            [("participants", 1), ("updated_at", -1)]
        )

        blocks = self.db.user_blocks
        await blocks.create_index(
            [("blocker_id", 1), ("blocked_id", 1)], unique=True
        )
        await blocks.create_index("blocker_id")

        keys = self.db.user_encryption_keys
        await keys.create_index("user_id", unique=True)

    def get_db(self):
        if self.db is None:
            raise RuntimeError("MongoDB not initialized")
        return self.db

    async def close(self):
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")


mongo_client = MongoClient()

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
        posts = self.db.posts
        await posts.create_index("post_id", unique=True)
        await posts.create_index("startup_id")
        await posts.create_index("author_user_id")
        await posts.create_index([("created_at", -1)])
        await posts.create_index([("startup_id", 1), ("created_at", -1)])
        await posts.create_index([("tags", 1), ("created_at", -1)])

        post_likes = self.db.post_likes
        await post_likes.create_index(
            [("post_id", 1), ("user_id", 1)], unique=True
        )
        await post_likes.create_index("post_id")

        post_comments = self.db.post_comments
        await post_comments.create_index("comment_id", unique=True)
        await post_comments.create_index("post_id")
        await post_comments.create_index([("post_id", 1), ("created_at", -1)])
        await post_comments.create_index("author_user_id")

    def get_db(self):
        if self.db is None:
            raise RuntimeError("MongoDB not initialized")
        return self.db

    async def close(self):
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")


mongo_client = MongoClient()

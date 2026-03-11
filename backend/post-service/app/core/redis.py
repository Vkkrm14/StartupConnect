import logging
from typing import Optional
import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisManager:
    def __init__(self):
        self.client: Optional[aioredis.Redis] = None

    async def connect(self):
        self.client = aioredis.from_url(
            settings.REDIS_URL, decode_responses=True, socket_connect_timeout=5,
        )
        await self.client.ping()
        logger.info("Redis connection established")

    async def close(self):
        if self.client:
            await self.client.close()
            logger.info("Redis connection closed")

    async def check_rate_limit(self, user_id: str, limit: int, window: int) -> bool:
        """Return True if within limit, False if limit exceeded."""
        key = f"post_rate:{user_id}"
        current = await self.client.get(key)
        if current and int(current) >= limit:
            return False
        pipe = self.client.pipeline()
        pipe.incr(key)
        pipe.expire(key, window)
        await pipe.execute()
        return True


redis_manager = RedisManager()

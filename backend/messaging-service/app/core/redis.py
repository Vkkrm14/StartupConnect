import logging
from typing import Optional, Any
import json
import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisManager:
    def __init__(self):
        self.client: Optional[aioredis.Redis] = None
        self.pubsub: Optional[aioredis.client.PubSub] = None

    async def connect(self):
        self.client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5,
        )
        await self.client.ping()
        logger.info("Redis connection established")

    async def close(self):
        if self.pubsub:
            await self.pubsub.unsubscribe()
            await self.pubsub.close()
        if self.client:
            await self.client.close()
            logger.info("Redis connection closed")

    # ---- Presence ----

    async def set_user_online(self, user_id: str, instance_id: str):
        key = f"presence:{user_id}"
        await self.client.hset(key, mapping={"status": "online", "instance": instance_id})
        await self.client.expire(key, 300)

    async def set_user_offline(self, user_id: str):
        await self.client.delete(f"presence:{user_id}")

    async def heartbeat(self, user_id: str):
        key = f"presence:{user_id}"
        if await self.client.exists(key):
            await self.client.expire(key, 300)

    async def get_user_presence(self, user_id: str) -> Optional[dict]:
        key = f"presence:{user_id}"
        data = await self.client.hgetall(key)
        return data if data else None

    # ---- WebSocket session mapping ----

    async def register_ws_session(self, user_id: str, session_id: str, instance_id: str):
        key = f"ws:sessions:{user_id}"
        await self.client.hset(key, session_id, instance_id)
        await self.client.expire(key, 3600)

    async def remove_ws_session(self, user_id: str, session_id: str):
        key = f"ws:sessions:{user_id}"
        await self.client.hdel(key, session_id)
        remaining = await self.client.hlen(key)
        if remaining == 0:
            await self.set_user_offline(user_id)

    async def get_user_sessions(self, user_id: str) -> dict:
        return await self.client.hgetall(f"ws:sessions:{user_id}")

    # ---- Typing indicators ----

    async def set_typing(self, user_id: str, conversation_id: str):
        key = f"typing:{conversation_id}:{user_id}"
        await self.client.setex(key, 5, "1")

    async def clear_typing(self, user_id: str, conversation_id: str):
        await self.client.delete(f"typing:{conversation_id}:{user_id}")

    async def get_typing_users(self, conversation_id: str) -> list:
        pattern = f"typing:{conversation_id}:*"
        keys = []
        async for key in self.client.scan_iter(match=pattern):
            user_id = key.split(":")[-1]
            keys.append(user_id)
        return keys

    # ---- Rate limiting ----

    async def check_rate_limit(self, user_id: str, limit: int, window: int = 60) -> bool:
        key = f"ratelimit:msg:{user_id}"
        current = await self.client.get(key)
        if current and int(current) >= limit:
            return False
        pipe = self.client.pipeline()
        pipe.incr(key)
        pipe.expire(key, window)
        await pipe.execute()
        return True

    # ---- Pub/Sub for cross-instance messaging ----

    async def publish(self, channel: str, data: dict):
        await self.client.publish(channel, json.dumps(data))

    async def subscribe(self, channel: str):
        self.pubsub = self.client.pubsub()
        await self.pubsub.subscribe(channel)
        return self.pubsub

    # ---- Delivery buffer ----

    async def buffer_message(self, user_id: str, message: dict, ttl: int = 86400):
        key = f"buffer:{user_id}"
        await self.client.rpush(key, json.dumps(message))
        await self.client.expire(key, ttl)

    async def get_buffered_messages(self, user_id: str) -> list:
        key = f"buffer:{user_id}"
        messages = await self.client.lrange(key, 0, -1)
        if messages:
            await self.client.delete(key)
        return [json.loads(m) for m in messages]


redis_manager = RedisManager()

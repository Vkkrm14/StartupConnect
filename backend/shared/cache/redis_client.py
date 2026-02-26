"""Redis Cache Client"""

from typing import Optional, Any
import json
import logging
from redis import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

class RedisCache:
    """Redis cache client with automatic serialization"""
    
    def __init__(self, redis_url: str, default_ttl: int = 3600):
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.client: Optional[Redis] = None
    
    def connect(self):
        """Connect to Redis"""
        try:
            self.client = Redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5
            )
            # Test connection
            self.client.ping()
            logger.info(f"✅ Connected to Redis: {self.redis_url}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {str(e)}")
            raise
    
    def close(self):
        """Close Redis connection"""
        if self.client:
            self.client.close()
            logger.info("🔌 Closed Redis connection")
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache
        
        Returns:
            Deserialized value or None if not found
        """
        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except RedisError as e:
            logger.error(f"Redis GET error for key '{key}': {str(e)}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds (None = use default)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            serialized = json.dumps(value)
            expire = ttl if ttl is not None else self.default_ttl
            
            self.client.setex(key, expire, serialized)
            return True
        except RedisError as e:
            logger.error(f"Redis SET error for key '{key}': {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            self.client.delete(key)
            return True
        except RedisError as e:
            logger.error(f"Redis DELETE error for key '{key}': {str(e)}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            return bool(self.client.exists(key))
        except RedisError as e:
            logger.error(f"Redis EXISTS error for key '{key}': {str(e)}")
            return False
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment counter"""
        try:
            return self.client.incrby(key, amount)
        except RedisError as e:
            logger.error(f"Redis INCR error for key '{key}': {str(e)}")
            return None
    
    async def set_with_pattern(self, pattern: str, value: Any, ttl: Optional[int] = None):
        """Set multiple keys matching a pattern"""
        # Implementation for bulk operations
        pass
    
    def get_client(self) -> Redis:
        """Get raw Redis client for advanced operations"""
        if not self.client:
            raise RuntimeError("Redis client not connected")
        return self.client

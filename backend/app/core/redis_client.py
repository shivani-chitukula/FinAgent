import logging
import time
import redis.asyncio as redis
from app.core.config import config

logger = logging.getLogger(__name__)

class InMemoryRedis:
    def __init__(self):
        self._store = {}

    async def get(self, key: str):
        if key not in self._store:
            return None
        val, expire_at = self._store[key]
        if expire_at is not None and time.time() > expire_at:
            del self._store[key]
            return None
        return val

    async def set(self, key: str, value: str, ex: int = None):
        expire_at = time.time() + ex if ex is not None else None
        self._store[key] = (value, expire_at)
        return True

    async def exists(self, key: str):
        val = await self.get(key)
        return 1 if val is not None else 0

class RedisFallbackClient:
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.real_client = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        self.fallback_client = InMemoryRedis()
        self.use_fallback = False
        self.tested = False

    async def _get_client(self):
        if self.use_fallback:
            return self.fallback_client
        if not self.tested:
            try:
                # Test connection asynchronously
                await self.real_client.ping()
                self.tested = True
                logger.info("Successfully connected to Redis.")
            except Exception as e:
                logger.warning(f"Redis connection failed ({e}). Falling back to in-memory cache.")
                self.use_fallback = True
                self.tested = True
                return self.fallback_client
        return self.real_client

    async def get(self, key: str):
        client = await self._get_client()
        try:
            return await client.get(key)
        except Exception as e:
            if not self.use_fallback:
                logger.warning(f"Redis get failed: {e}. Switching to in-memory cache.")
                self.use_fallback = True
                return await self.fallback_client.get(key)
            raise

    async def set(self, key: str, value: str, ex: int = None):
        client = await self._get_client()
        try:
            return await client.set(key, value, ex=ex)
        except Exception as e:
            if not self.use_fallback:
                logger.warning(f"Redis set failed: {e}. Switching to in-memory cache.")
                self.use_fallback = True
                return await self.fallback_client.set(key, value, ex=ex)
            raise

    async def exists(self, key: str):
        client = await self._get_client()
        try:
            return await client.exists(key)
        except Exception as e:
            if not self.use_fallback:
                logger.warning(f"Redis exists failed: {e}. Switching to in-memory cache.")
                self.use_fallback = True
                return await self.fallback_client.exists(key)
            raise

redis_client = RedisFallbackClient(config.REDIS_URL)

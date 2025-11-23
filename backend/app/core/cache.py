import redis.asyncio as redis
from app.core.config import settings

class Cache:
    def __init__(self):
        self.redis = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)

    async def get(self, key: str) -> str | None:
        return await self.redis.get(key)

    async def set(self, key: str, value: str, expire: int = None):
        await self.redis.set(key, value, ex=expire)

    async def close(self):
        await self.redis.close()

cache = Cache()

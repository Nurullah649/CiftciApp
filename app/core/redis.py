"""
Redis bağlantı yönetimi ve önbellekleme (caching) modülü.
"""
import json
import logging
import redis.asyncio as aioredis
from functools import wraps
from app.core.config import settings

logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self):
        self.redis = None

    async def connect(self):
        try:
            self.redis = await aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            await self.redis.ping()
            logger.info("✅ Redis bağlantısı başarılı.")
        except Exception as e:
            logger.error(f"❌ Redis bağlantı hatası: {e}")
            self.redis = None

    async def disconnect(self):
        if self.redis:
            await self.redis.close()
            logger.info("🔌 Redis bağlantısı kapatıldı.")

    async def get(self, key: str):
        if not self.redis:
            return None
        try:
            return await self.redis.get(key)
        except Exception as e:
            logger.warning(f"Redis GET hatası ({key}): {e}")
            return None

    async def set(self, key: str, value: str, expire: int = None):
        if not self.redis:
            return
        try:
            await self.redis.set(key, value, ex=expire)
        except Exception as e:
            logger.warning(f"Redis SET hatası ({key}): {e}")

redis_client = RedisClient()

def cache_response(expire: int = 3600):
    """
    Asenkron fonksiyonları Redis ile önbelleklemek için dekoratör.
    Sadece primitive tipler (int, str, float) ve dict/list döndüren fonksiyonlar için uygundur.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not redis_client.redis:
                return await func(*args, **kwargs)

            # Argümanlardan cache key oluştur
            key_parts = [func.__name__]
            for arg in args:
                key_parts.append(str(arg))
            for k, v in sorted(kwargs.items()):
                key_parts.append(f"{k}={v}")
            
            cache_key = ":".join(key_parts)
            
            cached_val = await redis_client.get(cache_key)
            if cached_val:
                try:
                    logger.info(f"⚡ Redis Cache Hit: {cache_key}")
                    return json.loads(cached_val)
                except json.JSONDecodeError:
                    return cached_val
            
            # Cache miss, fonksiyonu çalıştır
            result = await func(*args, **kwargs)
            
            if result is not None:
                try:
                    val_to_store = json.dumps(result)
                    await redis_client.set(cache_key, val_to_store, expire=expire)
                    logger.info(f"💾 Redis Cache Set: {cache_key}")
                except TypeError:
                    pass # Eğer dönen değer JSON serialize edilemiyorsa cacheleme
            
            return result
        return wrapper
    return decorator

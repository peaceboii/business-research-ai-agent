import os
import json
import time
from typing import Optional, Any
from loguru import logger

class CacheService:
    def __init__(self):
        self.redis_client = None
        self.memory_cache = {}
        self.memory_cache_expiry = {}
        self._init_redis()

    def _init_redis(self):
        redis_url = os.getenv("REDIS_URL")
        redis_host = os.getenv("REDIS_HOST", "127.0.0.1")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        redis_db = int(os.getenv("REDIS_DB", 0))
        
        try:
            import redis
            if redis_url:
                logger.info("CacheService: Connecting to Redis via URL...")
                self.redis_client = redis.Redis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_connect_timeout=2.0,
                    socket_timeout=2.0
                )
            else:
                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=redis_db,
                    decode_responses=True,
                    socket_connect_timeout=2.0,
                    socket_timeout=2.0
                )
            # Ping to verify connection
            self.redis_client.ping()
            logger.info("CacheService: Successfully connected to Redis.")
        except Exception as e:
            logger.warning(f"CacheService: Redis connection failed: {e}. Falling back to in-memory cache.")
            self.redis_client = None

    def get(self, key: str) -> Optional[str]:
        """
        Gets a cached value by key.
        """
        # If Redis is active
        if self.redis_client:
            try:
                val = self.redis_client.get(key)
                if val:
                    self._log_stat(key, hit=True)
                else:
                    self._log_stat(key, hit=False)
                return val
            except Exception as e:
                logger.error(f"CacheService: Redis GET error: {e}")
                
        # In-memory fallback
        now = time.time()
        if key in self.memory_cache:
            expiry = self.memory_cache_expiry.get(key, 0)
            if expiry > now:
                self._log_stat(key, hit=True)
                return self.memory_cache[key]
            else:
                # Expired
                del self.memory_cache[key]
                del self.memory_cache_expiry[key]
                
        self._log_stat(key, hit=False)
        return None

    def set(self, key: str, value: str, ttl: int = 86400) -> None:
        """
        Sets a key-value pair with TTL in seconds (default: 24 hours).
        """
        # Save to Redis if active
        if self.redis_client:
            try:
                self.redis_client.set(key, value, ex=ttl)
                return
            except Exception as e:
                logger.error(f"CacheService: Redis SET error: {e}")
                
        # Save to in-memory fallback
        self.memory_cache[key] = value
        self.memory_cache_expiry[key] = time.time() + ttl

    def get_json(self, key: str) -> Optional[Any]:
        val = self.get(key)
        if val:
            try:
                return json.loads(val)
            except Exception:
                return None
        return None

    def set_json(self, key: str, value: Any, ttl: int = 86400) -> None:
        try:
            self.set(key, json.dumps(value), ttl)
        except Exception as e:
            logger.error(f"CacheService: Failed to serialize JSON for cache key '{key}': {e}")

    def _log_stat(self, key: str, hit: bool):
        # We can increment SQLite statistics or print debug logs
        logger.debug(f"Cache {'HIT' if hit else 'MISS'} for key: {key}")
        
        # Async db update for cache stats could be triggered here or logged.
        # To avoid circular imports, we write custom query logic or simply log to database when connections are available.
        # We'll handle this in connection manager or api endpoints.
        pass

    def is_redis_active(self) -> bool:
        if not self.redis_client:
            return False
        try:
            return self.redis_client.ping()
        except Exception:
            return False

global_cache_service = CacheService()

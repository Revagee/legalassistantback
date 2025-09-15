import os
from redis.asyncio import Redis

from functools import lru_cache


@lru_cache
def get_redis() -> Redis:
    redis = Redis(
        host=os.getenv("REDIS_HOST"),
        port=os.getenv("REDIS_PORT"),
        decode_responses=True,
        username=os.getenv("REDIS_USERNAME"),
        password=os.getenv("REDIS_PASSWORD"),
    )
    return redis

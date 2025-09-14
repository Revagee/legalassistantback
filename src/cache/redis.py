import os
from redis.asyncio import Redis

# from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


# class RedisConfig(BaseSettings):
#     host: str = os.getenv("REDIS_HOST")
#     port: int = os.getenv("REDIS_PORT")
#     username: str = os.getenv("REDIS_USERNAME")
#     password: str = os.getenv("REDIS_PASSWORDS")
#     decode_responses: bool = True


@lru_cache
def get_redis() -> Redis:
    redis = Redis(
        host=os.getenv("REDIS_HOST"),
        port=os.getenv("REDIS_PORT"),
        decode_responses=True,
        username=os.getenv("REDIS_USERNAME"),
        password=os.getenv("REDIS_PASSWORDS"),
    )
    return redis

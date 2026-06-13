import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger("scms.jwt")

_redis_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(subject: str, role: str) -> str:
    expire = _now() + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload = {
        "sub": subject,
        "role": role,
        "type": "access",
        "exp": expire,
        "iat": _now(),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str) -> str:
    expire = _now() + timedelta(days=settings.jwt_refresh_token_expire_days)
    payload = {
        "sub": subject,
        "type": "refresh",
        "exp": expire,
        "iat": _now(),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


async def blacklist_token(jti: str, expires_in_seconds: int) -> None:
    try:
        r = await get_redis()
        await r.setex(f"blacklist:{jti}", expires_in_seconds, "1")
    except Exception:
        logger.warning("Redis unavailable — token blacklisting skipped for jti=%s", jti)


async def is_token_blacklisted(jti: str) -> bool:
    try:
        r = await get_redis()
        return await r.exists(f"blacklist:{jti}") == 1
    except Exception:
        logger.warning("Redis unavailable — assuming token is not blacklisted")
        return False

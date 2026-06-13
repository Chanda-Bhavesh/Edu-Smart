import secrets
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def generate_token(length: int = 32) -> str:
    return secrets.token_urlsafe(length)


def token_expiry(minutes: int = 0, hours: int = 0, days: int = 0) -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=minutes, hours=hours, days=days)

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.schemas.auth import RegisterRequest, LoginRequest
from app.utils.security import hash_password, verify_password, generate_token, token_expiry
from app.utils.jwt import create_access_token, create_refresh_token, decode_token, blacklist_token
from app.utils import email as email_utils
from app.config import settings


async def register_user(db: AsyncSession, payload: RegisterRequest) -> User:
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    verification_token = generate_token()
    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
        is_verified=False,
        verification_token=verification_token,
        verification_token_expires=token_expiry(hours=24),
    )
    db.add(user)
    await db.flush()

    try:
        email_utils.send_verification_email(user.email, user.full_name, verification_token)
    except Exception:
        pass

    return user


async def login_user(db: AsyncSession, payload: LoginRequest) -> dict:
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")
    if not user.is_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email not verified")

    user.last_login = datetime.now(timezone.utc)

    return {
        "access_token": create_access_token(str(user.id), user.role.value),
        "refresh_token": create_refresh_token(str(user.id)),
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value,
            "is_verified": user.is_verified,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat(),
        },
    }


async def verify_email(db: AsyncSession, token: str) -> None:
    result = await db.execute(select(User).where(User.verification_token == token))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification token")

    now = datetime.now(timezone.utc)
    expires = user.verification_token_expires
    if expires and expires.tzinfo is None:
        from datetime import timezone as tz
        expires = expires.replace(tzinfo=tz.utc)

    if not expires or now > expires:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification token has expired")

    user.is_verified = True
    user.verification_token = None
    user.verification_token_expires = None


async def resend_verification(db: AsyncSession, email: str) -> None:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or user.is_verified:
        return

    user.verification_token = generate_token()
    user.verification_token_expires = token_expiry(hours=24)

    try:
        email_utils.send_verification_email(user.email, user.full_name, user.verification_token)
    except Exception:
        pass


async def forgot_password(db: AsyncSession, email: str) -> None:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        return

    user.reset_token = generate_token()
    user.reset_token_expires = token_expiry(minutes=15)

    try:
        email_utils.send_password_reset_email(user.email, user.full_name, user.reset_token)
    except Exception:
        pass


async def reset_password(db: AsyncSession, token: str, new_password: str) -> None:
    result = await db.execute(select(User).where(User.reset_token == token))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reset token")

    now = datetime.now(timezone.utc)
    expires = user.reset_token_expires
    if expires and expires.tzinfo is None:
        from datetime import timezone as tz
        expires = expires.replace(tzinfo=tz.utc)

    if not expires or now > expires:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reset token has expired")

    user.hashed_password = hash_password(new_password)
    user.reset_token = None
    user.reset_token_expires = None


async def refresh_access_token(db: AsyncSession, refresh_token: str) -> dict:
    from jose import JWTError
    try:
        payload = decode_token(refresh_token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    return {
        "access_token": create_access_token(str(user.id), user.role.value),
        "refresh_token": create_refresh_token(str(user.id)),
        "token_type": "bearer",
    }

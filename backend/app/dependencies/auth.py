import uuid
from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User, UserRole
from app.utils.jwt import decode_token, is_token_blacklisted

_bearer = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(token)
    except JWTError:
        raise credentials_exception

    if payload.get("type") != "access":
        raise credentials_exception

    jti = payload.get("jti")
    if jti and await is_token_blacklisted(jti):
        raise credentials_exception

    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise credentials_exception

    return user


def require_role(*roles: UserRole) -> Callable:
    async def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[r.value for r in roles]}",
            )
        return current_user
    return _check


def get_current_student(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.student:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Students only")
    return current_user


def get_current_faculty(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.faculty:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Faculty only")
    return current_user


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in (UserRole.dept_admin, UserRole.org_admin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admins only")
    return current_user


def get_current_org_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.org_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization admins only")
    return current_user


def get_current_warden(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in (UserRole.warden, UserRole.org_admin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Wardens only")
    return current_user

from typing import AsyncGenerator, Any, Type, TypeVar
import jwt
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.errors import UnauthorizedException, NotFoundException, ForbiddenException
from app.core.security import decode_token
from app.db.session import get_db
from app.models.models import User

T = TypeVar("T")


async def get_current_user(
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise UnauthorizedException("Missing or invalid Authorization header")

    token = authorization.split(" ")[1]
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise UnauthorizedException("Invalid token type")
        user_id: str = payload.get("sub")
        if not user_id:
            raise UnauthorizedException("Invalid token payload")
    except jwt.ExpiredSignatureError:
        raise UnauthorizedException("Token has expired")
    except (jwt.InvalidTokenError, Exception):
        raise UnauthorizedException("Could not validate credentials")

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise UnauthorizedException("User not found")

    if not user.is_active:
        raise UnauthorizedException("Account is deactivated. Please contact support.")

    return user


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != "admin":
        raise ForbiddenException("Admin privileges required. Access denied.")
    return current_user


async def get_owned_or_404(
    db: AsyncSession,
    model: Type[T],
    resource_id: str,
    user: Any,
    allow_system_read: bool = False,
) -> T:
    """
    Enforce multi-user data isolation on a single database record:
    1. Look up the record by resource_id.
    2. If the record does not exist OR belongs to another user, return 404 Not Found.
       Returning 404 instead of 403 prevents attackers from probing/enumerating IDs.
    3. If allow_system_read is True and record.user_id is None, allow reading shared system defaults.
    4. Return the owned record.
    """
    user_id = user.id if hasattr(user, "id") else str(user)
    stmt = select(model).where(model.id == resource_id)
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()

    if not record:
        raise NotFoundException(f"{model.__name__} not found")

    if hasattr(record, "user_id"):
        if record.user_id == user_id:
            return record
        if allow_system_read and record.user_id is None:
            return record
        # Cross-user access returns 404 to prevent ID enumeration
        raise NotFoundException(f"{model.__name__} not found")

    return record



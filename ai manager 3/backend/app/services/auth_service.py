import logging
import re
import uuid
from typing import Tuple, Dict, Any, Optional
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.errors import BadRequestException, UnauthorizedException, ConflictException
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.models.models import User, AuditLog
from app.schemas.auth import RegisterRequest, LoginRequest

logger = logging.getLogger("finance_app.auth")


def normalize_phone(phone: Optional[str]) -> Optional[str]:
    """Helper to sanitize and format phone numbers if provided."""
    if not phone or not phone.strip():
        return None
    cleaned = re.sub(r"[\s\-\(\)\.]+", "", phone.strip())
    if len(cleaned) == 10 and cleaned.isdigit():
        return "+91" + cleaned
    if not cleaned.startswith("+"):
        return "+" + cleaned
    return cleaned


async def register_user(db: AsyncSession, req: RegisterRequest) -> User:
    email_clean = req.email.lower().strip()
    stmt = select(User).where(User.email == email_clean)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise ConflictException("A user with this email address already exists")

    clean_phone = normalize_phone(req.phone)
    if clean_phone:
        phone_stmt = select(User).where(User.phone == clean_phone)
        if (await db.execute(phone_stmt)).scalar_one_or_none():
            raise ConflictException("A user with this mobile number already exists")

    user = User(
        id=str(uuid.uuid4()),
        email=email_clean,
        password_hash=hash_password(req.password),
        name=req.name.strip(),
        currency=req.currency or "INR",
        timezone=req.timezone or "Asia/Kolkata",
        phone=clean_phone,
        phone_verified=True,
        email_verified=True,
        is_active=True,
        preferred_otp_channel="email",
        alert_preferences={"new_login": True, "account_changes": True, "security_settings": True, "consent_changes": True},
    )
    db.add(user)

    audit = AuditLog(
        id=str(uuid.uuid4()),
        user_id=user.id,
        action="USER_REGISTERED",
        entity="user",
        entity_id=user.id,
        meta_data={"email": user.email, "phone": clean_phone},
    )
    db.add(audit)

    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, req: LoginRequest, client_ip: str = "127.0.0.1") -> Tuple[User, str, str]:
    stmt = select(User).where(User.email == req.email.lower().strip())
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.password_hash):
        raise UnauthorizedException("Incorrect email or password")

    if not user.is_active:
        raise UnauthorizedException("Account is deactivated. Please contact support.")

    access_token = create_access_token(user.id, {"email": user.email, "role": user.role})
    refresh_token = create_refresh_token(user.id)

    audit = AuditLog(
        id=str(uuid.uuid4()),
        user_id=user.id,
        action="USER_LOGIN",
        entity="user",
        entity_id=user.id,
        meta_data={"email": user.email, "ip": client_ip},
    )
    db.add(audit)
    await db.commit()

    return user, access_token, refresh_token


async def refresh_access_token(db: AsyncSession, refresh_token: str) -> Tuple[str, User]:
    if not refresh_token:
        raise UnauthorizedException("Refresh token is required")

    try:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise UnauthorizedException("Invalid token type")
        user_id: str = payload.get("sub")
        if not user_id:
            raise UnauthorizedException("Invalid token payload")
    except jwt.ExpiredSignatureError:
        raise UnauthorizedException("Refresh token has expired, please log in again")
    except Exception:
        raise UnauthorizedException("Invalid refresh token")

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise UnauthorizedException("User not found")

    if not user.is_active:
        raise UnauthorizedException("Account is deactivated. Please contact support.")

    new_access_token = create_access_token(user.id, {"email": user.email, "role": user.role})
    return new_access_token, user

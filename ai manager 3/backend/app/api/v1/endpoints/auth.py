import logging
from typing import Optional
from fastapi import APIRouter, Depends, status, Request, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.limiter import limiter
from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.models import User
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    UserResponse,
    UpdateSecuritySettingsRequest,
)
from app.services import auth_service

logger = logging.getLogger("finance_app.auth")
router = APIRouter(prefix="/auth", tags=["Authentication"])


class RefreshTokenRequest(BaseModel):
    refresh_token: Optional[str] = None


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def register(
    request: Request,
    req: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    user = await auth_service.register_user(db, req)
    return user


@router.post("/login", response_model=TokenResponse)
@limiter.limit("15/minute")
async def login(
    request: Request,
    response: Response,
    req: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    client_ip = request.client.host if request.client else "127.0.0.1"
    user, access_token, refresh_token = await auth_service.authenticate_user(db, req, client_ip=client_ip)

    max_age = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=(settings.ENVIRONMENT == "production"),
        samesite="lax",
        max_age=max_age,
        path="/api/v1/auth",
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("20/minute")
async def refresh_token(
    request: Request,
    body: Optional[RefreshTokenRequest] = None,
    db: AsyncSession = Depends(get_db),
):
    token = request.cookies.get("refresh_token")
    if not token and body and body.refresh_token:
        token = body.refresh_token

    access_token, user = await auth_service.refresh_access_token(db, token)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(
        key="refresh_token",
        path="/api/v1/auth",
        httponly=True,
        samesite="lax",
    )
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/security")
async def get_security_settings(current_user: User = Depends(get_current_user)):
    return {
        "phone": current_user.phone,
        "phone_verified": current_user.phone_verified,
        "email_verified": current_user.email_verified,
        "alert_preferences": current_user.alert_preferences or {
            "new_login": True,
            "account_changes": True,
            "security_settings": True,
            "consent_changes": True,
        },
    }


@router.patch("/security", response_model=UserResponse)
async def update_security_settings(
    req: UpdateSecuritySettingsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if req.phone is not None:
        current_user.phone = req.phone.strip() if req.phone else None

    if req.alert_preferences is not None:
        current_prefs = current_user.alert_preferences or {}
        current_prefs.update(req.alert_preferences)
        current_user.alert_preferences = current_prefs

    await db.commit()
    await db.refresh(current_user)
    return current_user

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    name: str = Field(..., min_length=2, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    currency: Optional[str] = Field("INR", max_length=10)
    timezone: Optional[str] = Field("Asia/Kolkata", max_length=50)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UpdateSecuritySettingsRequest(BaseModel):
    phone: Optional[str] = None
    alert_preferences: Optional[Dict[str, bool]] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    name: str
    currency: str
    timezone: str
    role: str = "customer"
    is_active: bool = True
    is_demo: bool = False
    segment: Optional[str] = None
    phone: Optional[str] = None
    phone_verified: bool = True
    email_verified: bool = True
    alert_preferences: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

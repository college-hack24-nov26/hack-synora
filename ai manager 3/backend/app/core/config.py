import os
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl, field_validator, model_validator

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
ROOT_DIR = BACKEND_DIR.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            str(BACKEND_DIR / ".env"),
            str(ROOT_DIR / ".env"),
            ".env",
        ),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    PROJECT_NAME: str = "AI Personal Finance Manager"
    ENVIRONMENT: str = "development"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "super-secret-key-change-in-production-min-32-chars-long"

    # Field-level Encryption (Fernet 32-byte base64 key)
    ENCRYPTION_KEY: Optional[str] = None

    # CORS
    FRONTEND_ORIGIN: str = "http://localhost:3000"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./test.db"
    DATABASE_URL_SYNC: str = "sqlite:///./test.db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT Authentication
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # Uploads
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB

    # AI / LLM
    LLM_PROVIDER: str = "mock"  # mock, anthropic, gemini, openai
    ANTHROPIC_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    LLM_MODEL_FAST: str = "claude-haiku-5-5"
    LLM_MODEL_SMART: str = "claude-sonnet-5-5"
    LLM_DAILY_LIMIT_PER_USER: int = 50

    # OTP & Multi-Channel Delivery (SMS & Email)
    OTP_PROVIDER: Optional[str] = None  # Backward compatibility
    OTP_SMS_PROVIDER: str = "console"  # console, msg91, twilio
    SMS_PROVIDER: Optional[str] = None  # Alias for OTP_SMS_PROVIDER
    OTP_EMAIL_PROVIDER: str = "console"  # console, smtp, resend, sendgrid, brevo
    OTP_RESEND_COOLDOWN_SECONDS: int = 30
    OTP_MAX_ATTEMPTS: int = 5
    OTP_MAX_HOURLY_SENDS: int = 5
    OTP_EXPIRY_MINUTES: int = 5

    # SMTP Settings (Gmail, Mailpit, Custom)
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_USER: Optional[str] = None  # Alias
    SMTP_PASSWORD: Optional[str] = None
    SMTP_PASS: Optional[str] = None  # Alias
    SMTP_USE_TLS: bool = True
    EMAIL_FROM_NAME: str = "FinTrack AI"
    EMAIL_FROM_ADDRESS: str = "noreply@fintrack.ai"
    EMAIL_FROM: Optional[str] = None  # Alias

    # Email API Keys
    RESEND_API_KEY: Optional[str] = None
    SENDGRID_API_KEY: Optional[str] = None
    BREVO_API_KEY: Optional[str] = None

    # SMS Provider API Keys
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_FROM_NUMBER: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None  # Alias
    MSG91_AUTH_KEY: Optional[str] = None
    MSG91_SENDER_ID: Optional[str] = None
    MSG91_TEMPLATE_ID: Optional[str] = None

    @property
    def active_sms_provider(self) -> str:
        if self.SMS_PROVIDER:
            return self.SMS_PROVIDER.lower().strip()
        if self.OTP_SMS_PROVIDER:
            return self.OTP_SMS_PROVIDER.lower().strip()
        if self.OTP_PROVIDER and self.OTP_PROVIDER.lower().strip() in ["console", "msg91", "twilio"]:
            return self.OTP_PROVIDER.lower().strip()
        return "console"

    @property
    def active_email_provider(self) -> str:
        if self.OTP_EMAIL_PROVIDER:
            return self.OTP_EMAIL_PROVIDER.lower().strip()
        if self.OTP_PROVIDER and self.OTP_PROVIDER.lower().strip() in ["console", "smtp", "resend", "sendgrid", "brevo"]:
            return self.OTP_PROVIDER.lower().strip()
        return "console"

    @property
    def active_smtp_user(self) -> Optional[str]:
        return self.SMTP_USER or self.SMTP_USERNAME

    @property
    def active_smtp_pass(self) -> Optional[str]:
        val = self.SMTP_PASS or self.SMTP_PASSWORD
        if val:
            return val.replace(" ", "")  # Strip whitespace from Google App Passwords
        return None

    @property
    def active_email_from(self) -> str:
        return self.EMAIL_FROM or self.EMAIL_FROM_ADDRESS

    @property
    def active_twilio_from(self) -> Optional[str]:
        return self.TWILIO_PHONE_NUMBER or self.TWILIO_FROM_NUMBER

    @model_validator(mode="after")
    def validate_production_keys(self) -> "Settings":
        if self.ENVIRONMENT.lower() == "production":
            if self.SECRET_KEY == "super-secret-key-change-in-production-min-32-chars-long":
                raise ValueError("In production, SECRET_KEY must be overridden with a secure, unique 32+ character key.")
            if not self.ENCRYPTION_KEY or self.ENCRYPTION_KEY == "dGVzdC1lbmNyeXB0aW9uLWtleS1kZXYtMzJieXRlczE=":
                raise ValueError("In production, ENCRYPTION_KEY must be configured with a valid Fernet key.")
        return self

    @property
    def active_encryption_key(self) -> str:
        if self.ENCRYPTION_KEY:
            return self.ENCRYPTION_KEY
        return "dGVzdC1lbmNyeXB0aW9uLWtleS1kZXYtMzJieXRlczE="

    @property
    def cors_origins(self) -> List[str]:
        origins = [self.FRONTEND_ORIGIN.rstrip("/")]
        if self.ENVIRONMENT == "development":
            origins.extend(["http://localhost:3000", "http://127.0.0.1:3000"])
        return list(set(origins))


settings = Settings()


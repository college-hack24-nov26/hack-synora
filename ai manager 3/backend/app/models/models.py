import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Text,
    BigInteger,
    Boolean,
    Numeric,
    DateTime,
    ForeignKey,
    Integer,
    UniqueConstraint,
    Index,
    text,
)
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.custom_types import GUID, JSONType, EncryptedText


def utc_now():
    return datetime.now(timezone.utc)


def gen_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(GUID, primary_key=True, default=gen_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    currency = Column(String(10), default="INR", nullable=False)
    timezone = Column(String(50), default="Asia/Kolkata", nullable=False)
    role = Column(String(20), default="customer", nullable=False)  # customer, admin
    is_active = Column(Boolean, default=True, nullable=False)
    is_demo = Column(Boolean, default=False, nullable=False)
    segment = Column(String(50), nullable=True)  # student, professional, business, freelancer, family
    phone = Column(String(20), nullable=True)
    phone_verified = Column(Boolean, default=False, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)
    preferred_otp_channel = Column(String(10), default="email", nullable=False)  # sms, email, both
    alert_preferences = Column(JSONType, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    accounts = relationship("Account", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    categories = relationship("Category", back_populates="user", cascade="all, delete-orphan")
    imports = relationship("Import", back_populates="user", cascade="all, delete-orphan")
    merchant_rules = relationship("MerchantRule", back_populates="user", cascade="all, delete-orphan")
    budgets = relationship("Budget", back_populates="user", cascade="all, delete-orphan")
    forecasts = relationship("Forecast", back_populates="user", cascade="all, delete-orphan")
    savings_suggestions = relationship("SavingsSuggestion", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    consents = relationship("Consent", back_populates="user", cascade="all, delete-orphan")


class Account(Base):
    __tablename__ = "accounts"

    id = Column(GUID, primary_key=True, default=gen_uuid)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    type = Column(String(50), nullable=False)  # savings, current, credit_card, wallet, cash
    last4 = Column(String(4), nullable=True)
    opening_balance_minor = Column(BigInteger, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account", cascade="all, delete-orphan")


class Category(Base):
    __tablename__ = "categories"

    id = Column(GUID, primary_key=True, default=gen_uuid)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)  # null = system default
    name = Column(String(100), nullable=False)
    parent_id = Column(GUID, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    icon = Column(String(50), nullable=True)
    color = Column(String(20), nullable=True)
    is_income = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="categories")
    parent = relationship("Category", remote_side=[id], backref="subcategories")
    transactions = relationship("Transaction", back_populates="category")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(GUID, primary_key=True, default=gen_uuid)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    account_id = Column(GUID, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    amount_minor = Column(BigInteger, nullable=False)  # ALWAYS in paise / integer minor units
    direction = Column(String(10), nullable=False)  # debit or credit
    currency = Column(String(10), default="INR", nullable=False)
    txn_date = Column(DateTime(timezone=True), nullable=False)  # ALWAYS in UTC
    merchant_raw = Column(EncryptedText, nullable=True)
    merchant_normalized = Column(String(255), nullable=True)
    description = Column(EncryptedText, nullable=True)
    category_id = Column(GUID, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)
    category_source = Column(String(20), default="rule", nullable=False)  # rule, ml, user
    category_confidence = Column(Numeric(5, 4), default=1.0, nullable=False)
    needs_review = Column(Boolean, default=False, nullable=False)
    source = Column(String(20), nullable=False)  # sms, csv, pdf, manual
    import_id = Column(GUID, ForeignKey("imports.id", ondelete="SET NULL"), nullable=True)
    dedupe_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # Soft delete

    user = relationship("User", back_populates="transactions")
    account = relationship("Account", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")
    import_record = relationship("Import", back_populates="transactions")

    __table_args__ = (
        UniqueConstraint("user_id", "dedupe_hash", name="uq_user_dedupe_hash"),
        Index("ix_transactions_user_txn_date", "user_id", "txn_date"),
        Index("ix_transactions_user_txn_date_desc", "user_id", text("txn_date DESC")),
        Index("ix_transactions_user_category", "user_id", "category_id"),
        Index("ix_transactions_user_needs_review", "user_id", "needs_review"),
    )


class Import(Base):
    __tablename__ = "imports"

    id = Column(GUID, primary_key=True, default=gen_uuid)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    source_type = Column(String(20), nullable=False)  # sms, csv, xlsx, pdf
    file_name = Column(EncryptedText, nullable=True)
    status = Column(String(20), default="pending", nullable=False)  # pending, processing, done, failed
    total_rows = Column(Integer, default=0, nullable=False)
    parsed_rows = Column(Integer, default=0, nullable=False)
    failed_rows = Column(Integer, default=0, nullable=False)
    error_report = Column(JSONType, default=list, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="imports")
    transactions = relationship("Transaction", back_populates="import_record")


class MerchantRule(Base):
    __tablename__ = "merchant_rules"

    id = Column(GUID, primary_key=True, default=gen_uuid)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    pattern = Column(String(255), nullable=False)  # regex or keyword
    category_id = Column(GUID, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    priority = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="merchant_rules")
    category = relationship("Category")

    __table_args__ = (
        Index("ix_merchant_rules_user_priority", "user_id", "priority"),
    )


class Budget(Base):
    __tablename__ = "budgets"

    id = Column(GUID, primary_key=True, default=gen_uuid)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(GUID, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    month = Column(String(7), nullable=False)  # YYYY-MM
    limit_minor = Column(BigInteger, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="budgets")
    category = relationship("Category")

    __table_args__ = (
        UniqueConstraint("user_id", "category_id", "month", name="uq_user_category_month_budget"),
    )


class Forecast(Base):
    __tablename__ = "forecasts"

    id = Column(GUID, primary_key=True, default=gen_uuid)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    target_month = Column(String(7), nullable=False)  # YYYY-MM
    category_id = Column(GUID, ForeignKey("categories.id", ondelete="CASCADE"), nullable=True)
    predicted_minor = Column(BigInteger, nullable=False)
    lower_bound_minor = Column(BigInteger, nullable=False)
    upper_bound_minor = Column(BigInteger, nullable=False)
    model_version = Column(String(50), default="v1-stat", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    user = relationship("User", back_populates="forecasts")
    category = relationship("Category")


class SavingsSuggestion(Base):
    __tablename__ = "savings_suggestions"

    id = Column(GUID, primary_key=True, default=gen_uuid)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(50), nullable=False)  # subscription_cancel, dining_reduction, etc.
    title = Column(String(255), nullable=False)
    detail = Column(Text, nullable=False)
    estimated_saving_minor = Column(BigInteger, default=0, nullable=False)
    status = Column(String(20), default="new", nullable=False)  # new, accepted, dismissed
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="savings_suggestions")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(GUID, primary_key=True, default=gen_uuid)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(String(100), nullable=False)
    entity = Column(String(100), nullable=False)
    entity_id = Column(String(36), nullable=True)
    meta_data = Column(JSONType, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    user = relationship("User", back_populates="audit_logs")


class Consent(Base):
    __tablename__ = "consents"

    id = Column(GUID, primary_key=True, default=gen_uuid)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    consent_type = Column(String(50), nullable=False)  # sms_import, statement_upload, share_with_bank
    granted = Column(Boolean, default=True, nullable=False)
    granted_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    policy_version = Column(String(20), default="1.0", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="consents")

    __table_args__ = (
        UniqueConstraint("user_id", "consent_type", name="uq_user_consent_type"),
        Index("ix_consents_user_type", "user_id", "consent_type"),
    )



import uuid
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.types import TypeDecorator, CHAR, JSON, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB as PG_JSONB
from app.core.config import settings

_fernet_instance = None


def get_fernet() -> Fernet:
    global _fernet_instance
    if _fernet_instance is None:
        key = settings.active_encryption_key
        if isinstance(key, str):
            key = key.encode("utf-8")
        _fernet_instance = Fernet(key)
    return _fernet_instance


def reset_fernet(key: str = None):
    """Helper to reset or rotate fernet instance during runtime/tests."""
    global _fernet_instance
    if key:
        if isinstance(key, str):
            key = key.encode("utf-8")
        _fernet_instance = Fernet(key)
    else:
        _fernet_instance = None


class EncryptedText(TypeDecorator):
    """SQLAlchemy TypeDecorator for at-rest field encryption using Fernet.
    Encrypts string values before writing to the database,
    and decrypts them transparently on read.
    """
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if not isinstance(value, str):
            value = str(value)
        fernet = get_fernet()
        return fernet.encrypt(value.encode("utf-8")).decode("utf-8")

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        fernet = get_fernet()
        try:
            return fernet.decrypt(value.encode("utf-8")).decode("utf-8")
        except (InvalidToken, Exception):
            # Fallback for plain text or legacy rows
            return value


class GUID(TypeDecorator):
    """Platform-independent GUID/UUID type.
    Uses PostgreSQL's UUID type, otherwise uses CHAR(36).
    """
    impl = CHAR(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=False))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == "postgresql":
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return str(uuid.UUID(str(value)))
            return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return str(value)


class JSONType(TypeDecorator):
    """Platform-independent JSON type.
    Uses PostgreSQL's JSONB type, otherwise standard JSON.
    """
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_JSONB())
        else:
            return dialect.type_descriptor(JSON())


import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy import select, and_, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import Consent, Transaction, Import, AuditLog, utc_now
from app.core.errors import BadRequestException, NotFoundException

VALID_CONSENT_TYPES = {"sms_import", "statement_upload", "share_with_bank", "ai_processing"}


async def get_user_consents(db: AsyncSession, user_id: str) -> List[Consent]:
    stmt = select(Consent).where(Consent.user_id == user_id)
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def has_active_consent(db: AsyncSession, user_id: str, consent_type: str) -> bool:
    stmt = select(Consent).where(
        and_(
            Consent.user_id == user_id,
            Consent.consent_type == consent_type,
            Consent.granted == True,
            Consent.revoked_at.is_(None),
        )
    )
    res = await db.execute(stmt)
    return res.scalar_one_or_none() is not None


async def grant_consent(
    db: AsyncSession,
    user_id: str,
    consent_type: str,
    policy_version: str = "1.0",
) -> Consent:
    if consent_type not in VALID_CONSENT_TYPES:
        raise BadRequestException(f"Invalid consent type '{consent_type}'. Must be one of: {VALID_CONSENT_TYPES}")

    stmt = select(Consent).where(and_(Consent.user_id == user_id, Consent.consent_type == consent_type))
    res = await db.execute(stmt)
    consent = res.scalar_one_or_none()

    now = utc_now()
    if consent:
        consent.granted = True
        consent.granted_at = now
        consent.revoked_at = None
        consent.policy_version = policy_version
        consent.updated_at = now
    else:
        consent = Consent(
            id=str(uuid.uuid4()),
            user_id=user_id,
            consent_type=consent_type,
            granted=True,
            granted_at=now,
            revoked_at=None,
            policy_version=policy_version,
            created_at=now,
            updated_at=now,
        )
        db.add(consent)

    audit = AuditLog(
        id=str(uuid.uuid4()),
        user_id=user_id,
        action="CONSENT_GRANTED",
        entity="consent",
        entity_id=consent.id,
        meta_data={"consent_type": consent_type, "policy_version": policy_version},
    )
    db.add(audit)
    await db.commit()
    await db.refresh(consent)
    return consent


async def revoke_consent(
    db: AsyncSession,
    user_id: str,
    consent_type: str,
    delete_data: bool = False,
) -> Dict[str, Any]:
    if consent_type not in VALID_CONSENT_TYPES:
        raise BadRequestException(f"Invalid consent type '{consent_type}'. Must be one of: {VALID_CONSENT_TYPES}")

    stmt = select(Consent).where(and_(Consent.user_id == user_id, Consent.consent_type == consent_type))
    res = await db.execute(stmt)
    consent = res.scalar_one_or_none()

    now = utc_now()
    if not consent:
        # Create an explicitly revoked record
        consent = Consent(
            id=str(uuid.uuid4()),
            user_id=user_id,
            consent_type=consent_type,
            granted=False,
            granted_at=now,
            revoked_at=now,
            policy_version="1.0",
            created_at=now,
            updated_at=now,
        )
        db.add(consent)
    else:
        consent.granted = False
        consent.revoked_at = now
        consent.updated_at = now

    deleted_count = 0
    if delete_data:
        if consent_type == "sms_import":
            target_sources = ["sms"]
        elif consent_type == "statement_upload":
            target_sources = ["csv", "pdf", "xlsx"]
        else:
            target_sources = []

        if target_sources:
            # Delete transactions matching source and user
            del_txns_stmt = (
                delete(Transaction)
                .where(
                    and_(
                        Transaction.user_id == user_id,
                        Transaction.source.in_(target_sources),
                    )
                )
            )
            res_txns = await db.execute(del_txns_stmt)
            deleted_count = res_txns.rowcount or 0

            # Delete import records matching source_type
            del_imports_stmt = (
                delete(Import)
                .where(
                    and_(
                        Import.user_id == user_id,
                        Import.source_type.in_(target_sources),
                    )
                )
            )
            await db.execute(del_imports_stmt)

    audit = AuditLog(
        id=str(uuid.uuid4()),
        user_id=user_id,
        action="CONSENT_REVOKED",
        entity="consent",
        entity_id=consent.id,
        meta_data={
            "consent_type": consent_type,
            "data_deleted": delete_data,
            "deleted_transactions": deleted_count,
        },
    )
    db.add(audit)
    await db.commit()
    await db.refresh(consent)

    return {
        "consent": consent,
        "data_deleted": delete_data,
        "deleted_transactions": deleted_count,
    }


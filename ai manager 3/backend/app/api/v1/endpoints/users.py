import uuid
from typing import Dict, Any
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, delete
from app.core.dependencies import get_current_user
from app.core.security import verify_password
from app.core.errors import UnauthorizedException
from app.db.session import get_db
from app.models.models import (
    User,
    Account,
    Transaction,
    Category,
    Import,
    MerchantRule,
    Budget,
    Forecast,
    SavingsSuggestion,
    Consent,
    AuditLog,
)

router = APIRouter(prefix="/users", tags=["users"])


class DeleteDataRequest(BaseModel):
    password: str = Field(..., min_length=1, description="Account password for confirmation")


@router.get("/me/export")
async def export_my_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Promise 4 & Data Control: Full portability export of all user financial records."""
    user_id = current_user.id

    # 1. Accounts
    accs_res = await db.execute(select(Account).where(Account.user_id == user_id))
    accounts = [
        {
            "id": a.id,
            "name": a.name,
            "type": a.type,
            "last4": a.last4,
            "opening_balance_minor": a.opening_balance_minor,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in accs_res.scalars().all()
    ]

    # 2. Transactions
    txns_res = await db.execute(
        select(Transaction).where(and_(Transaction.user_id == user_id, Transaction.deleted_at.is_(None)))
    )
    transactions = [
        {
            "id": t.id,
            "account_id": t.account_id,
            "amount_minor": t.amount_minor,
            "direction": t.direction,
            "currency": t.currency,
            "txn_date": t.txn_date.isoformat() if t.txn_date else None,
            "merchant_raw": t.merchant_raw,
            "merchant_normalized": t.merchant_normalized,
            "description": t.description,
            "category_id": t.category_id,
            "source": t.source,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in txns_res.scalars().all()
    ]

    # 3. Custom Categories
    cats_res = await db.execute(select(Category).where(Category.user_id == user_id))
    categories = [
        {
            "id": c.id,
            "name": c.name,
            "icon": c.icon,
            "color": c.color,
            "is_income": c.is_income,
        }
        for c in cats_res.scalars().all()
    ]

    # 4. Consents
    cons_res = await db.execute(select(Consent).where(Consent.user_id == user_id))
    consents = [
        {
            "consent_type": c.consent_type,
            "granted": c.granted,
            "granted_at": c.granted_at.isoformat() if c.granted_at else None,
            "revoked_at": c.revoked_at.isoformat() if c.revoked_at else None,
            "policy_version": c.policy_version,
        }
        for c in cons_res.scalars().all()
    ]

    # 5. Imports
    imps_res = await db.execute(select(Import).where(Import.user_id == user_id))
    imports = [
        {
            "id": i.id,
            "source_type": i.source_type,
            "file_name": i.file_name,
            "status": i.status,
            "total_rows": i.total_rows,
            "parsed_rows": i.parsed_rows,
            "created_at": i.created_at.isoformat() if i.created_at else None,
        }
        for i in imps_res.scalars().all()
    ]

    return {
        "export_metadata": {
            "app": "AI Personal Finance Manager",
            "version": "1.0.0",
            "user_id": current_user.id,
            "user_name": current_user.name,
            "user_email": current_user.email,
            "exported_at": current_user.created_at.isoformat() if current_user.created_at else None,
        },
        "accounts": accounts,
        "transactions": transactions,
        "custom_categories": categories,
        "consents": consents,
        "imports": imports,
    }


@router.delete("/me/data", status_code=status.HTTP_200_OK)
async def delete_my_data(
    payload: DeleteDataRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Promise 4 & Data Control: Permanently wipes all financial statements, accounts, and transactions."""
    if not verify_password(payload.password, current_user.password_hash):
        raise UnauthorizedException("Incorrect password. Password confirmation is required to delete financial data.")

    user_id = current_user.id

    # Cascade deletes from child models
    await db.execute(delete(Transaction).where(Transaction.user_id == user_id))
    await db.execute(delete(Import).where(Import.user_id == user_id))
    await db.execute(delete(Account).where(Account.user_id == user_id))
    await db.execute(delete(MerchantRule).where(MerchantRule.user_id == user_id))
    await db.execute(delete(Budget).where(Budget.user_id == user_id))
    await db.execute(delete(Forecast).where(Forecast.user_id == user_id))
    await db.execute(delete(SavingsSuggestion).where(SavingsSuggestion.user_id == user_id))
    await db.execute(delete(Category).where(Category.user_id == user_id))

    audit = AuditLog(
        id=str(uuid.uuid4()),
        user_id=user_id,
        action="USER_FINANCIAL_DATA_PURGED",
        entity="user_data",
        entity_id=user_id,
        meta_data={"action": "full_financial_data_deletion"},
    )
    db.add(audit)
    await db.commit()

    return {
        "status": "success",
        "message": "All financial accounts, transactions, statements, and analytics have been permanently deleted.",
    }

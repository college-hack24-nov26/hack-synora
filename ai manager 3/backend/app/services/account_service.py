import uuid
from typing import List, Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_owned_or_404
from app.core.errors import NotFoundException, BadRequestException
from app.models.models import Account, Transaction, AuditLog
from app.schemas.account import AccountCreate, AccountUpdate, AccountResponse


async def create_account(db: AsyncSession, user_id: str, req: AccountCreate) -> Account:
    account = Account(
        id=str(uuid.uuid4()),
        user_id=user_id,
        name=req.name.strip(),
        type=req.type,
        last4=req.last4,
        opening_balance_minor=req.opening_balance_minor,
    )
    db.add(account)

    audit = AuditLog(
        id=str(uuid.uuid4()),
        user_id=user_id,
        action="ACCOUNT_CREATED",
        entity="account",
        entity_id=account.id,
        meta_data={"name": account.name, "type": account.type},
    )
    db.add(audit)

    await db.commit()
    await db.refresh(account)
    return account


async def get_user_accounts(db: AsyncSession, user_id: str) -> List[AccountResponse]:
    # Query accounts for user
    stmt = select(Account).where(Account.user_id == user_id).order_by(Account.created_at.asc())
    result = await db.execute(stmt)
    accounts = result.scalars().all()

    account_responses = []
    for acc in accounts:
        # Calculate current balance from opening balance + credits - debits
        credit_stmt = select(func.coalesce(func.sum(Transaction.amount_minor), 0)).where(
            and_(
                Transaction.user_id == user_id,
                Transaction.account_id == acc.id,
                Transaction.direction == "credit",
                Transaction.deleted_at.is_(None),
            )
        )
        debit_stmt = select(func.coalesce(func.sum(Transaction.amount_minor), 0)).where(
            and_(
                Transaction.user_id == user_id,
                Transaction.account_id == acc.id,
                Transaction.direction == "debit",
                Transaction.deleted_at.is_(None),
            )
        )
        credits = (await db.execute(credit_stmt)).scalar_one()
        debits = (await db.execute(debit_stmt)).scalar_one()
        current_balance = acc.opening_balance_minor + credits - debits

        res = AccountResponse.model_validate(acc)
        res.current_balance_minor = current_balance
        account_responses.append(res)

    return account_responses


async def get_account_by_id(db: AsyncSession, user_id: str, account_id: str) -> Account:
    return await get_owned_or_404(db, Account, account_id, user_id)


async def update_account(db: AsyncSession, user_id: str, account_id: str, req: AccountUpdate) -> Account:
    account = await get_owned_or_404(db, Account, account_id, user_id)

    if req.name is not None:
        account.name = req.name.strip()
    if req.type is not None:
        account.type = req.type
    if req.last4 is not None:
        account.last4 = req.last4
    if req.opening_balance_minor is not None:
        account.opening_balance_minor = req.opening_balance_minor

    audit = AuditLog(
        id=str(uuid.uuid4()),
        user_id=user_id,
        action="ACCOUNT_UPDATED",
        entity="account",
        entity_id=account.id,
        meta_data={"name": account.name},
    )
    db.add(audit)

    await db.commit()
    await db.refresh(account)
    return account


async def delete_account(db: AsyncSession, user_id: str, account_id: str) -> None:
    account = await get_owned_or_404(db, Account, account_id, user_id)
    await db.delete(account)

    audit = AuditLog(
        id=str(uuid.uuid4()),
        user_id=user_id,
        action="ACCOUNT_DELETED",
        entity="account",
        entity_id=account_id,
        meta_data={"name": account.name},
    )
    db.add(audit)
    await db.commit()


from typing import List
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.models import User
from app.schemas.account import (
    AccountCreate,
    AccountUpdate,
    AccountResponse,
)
from app.services import account_service

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    req: AccountCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account = await account_service.create_account(db, current_user.id, req)
    res = AccountResponse.model_validate(account)
    res.current_balance_minor = account.opening_balance_minor
    return res


@router.get("", response_model=List[AccountResponse])
async def list_accounts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await account_service.get_user_accounts(db, current_user.id)


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account = await account_service.get_account_by_id(db, current_user.id, account_id)
    accounts = await account_service.get_user_accounts(db, current_user.id)
    for a in accounts:
        if a.id == account_id:
            return a
    res = AccountResponse.model_validate(account)
    res.current_balance_minor = account.opening_balance_minor
    return res


@router.patch("/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: str,
    req: AccountUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account = await account_service.update_account(db, current_user.id, account_id, req)
    res = AccountResponse.model_validate(account)
    return res


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await account_service.delete_account(db, current_user.id, account_id)
    return None

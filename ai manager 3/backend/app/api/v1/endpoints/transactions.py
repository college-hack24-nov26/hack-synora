import math
from typing import Optional, List, Literal
from datetime import datetime
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.models import User
from app.schemas.transaction import (
    TransactionOut,
    TransactionDetailOut,
    TransactionListResponse,
    TransactionSummaryResponse,
    TransactionCreate,
    TransactionUpdate,
)
from app.services import transaction_service, categorization_service

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=TransactionListResponse)
async def get_transactions(
    page: int = Query(1, ge=1, description="Page number starting at 1"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: Optional[int] = Query(None, ge=0),
    account_id: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
    direction: Optional[str] = Query(None, pattern="^(debit|credit)$"),
    search: Optional[str] = Query(None, description="Search merchant name or description"),
    start_date: Optional[datetime] = Query(None, description="Filter transactions after this UTC datetime"),
    end_date: Optional[datetime] = Query(None, description="Filter transactions before this UTC datetime"),
    min_amount_minor: Optional[int] = Query(None, ge=0),
    max_amount_minor: Optional[int] = Query(None, ge=0),
    needs_review: Optional[bool] = Query(None, description="Filter transactions needing manual review"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    computed_offset = offset if offset is not None else (page - 1) * limit
    transactions, total = await transaction_service.list_transactions(
        db=db,
        user_id=current_user.id,
        account_id=account_id,
        category_id=category_id,
        direction=direction,
        search=search,
        start_date=start_date,
        end_date=end_date,
        min_amount_minor=min_amount_minor,
        max_amount_minor=max_amount_minor,
        needs_review=needs_review,
        limit=limit,
        offset=computed_offset,
    )

    total_pages = math.ceil(total / limit) if total > 0 else 1
    current_page = (computed_offset // limit) + 1

    return {
        "items": transactions,
        "total": total,
        "page": current_page,
        "limit": limit,
        "total_pages": total_pages,
    }


@router.get("/summary", response_model=TransactionSummaryResponse)
async def get_transactions_summary(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    account_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns aggregated transaction metrics: total spent, income, count, and top categories."""
    return await transaction_service.get_transactions_summary(
        db=db,
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
        account_id=account_id,
    )


@router.get("/needs-review", response_model=TransactionListResponse)
async def get_needs_review_transactions(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetches user-scoped transactions where category assignment requires review."""
    offset = (page - 1) * limit
    transactions, total = await transaction_service.list_transactions(
        db=db,
        user_id=current_user.id,
        needs_review=True,
        limit=limit,
        offset=offset,
    )
    total_pages = math.ceil(total / limit) if total > 0 else 1
    return {
        "items": transactions,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
    }


@router.post("/recategorize")
async def recategorize_transactions(
    only_needs_review: bool = Query(False, description="Whether to re-categorize only needs-review transactions"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Re-runs rule and model categorization for the user's transactions (user-scoped)."""
    return await categorization_service.recategorize_user_transactions(
        db=db,
        user_id=current_user.id,
        only_needs_review=only_needs_review,
    )


@router.post("", response_model=TransactionDetailOut, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    payload: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    txn = await transaction_service.create_manual_transaction(
        db=db,
        user_id=current_user.id,
        account_id=payload.account_id,
        amount_minor=payload.amount_minor,
        direction=payload.direction,
        merchant=payload.merchant,
        category_id=payload.category_id,
        txn_date=payload.txn_date,
        description=payload.description,
    )
    return await transaction_service.get_transaction_detail(
        db=db,
        user_id=current_user.id,
        txn_id=txn.id,
    )


@router.get("/{transaction_id}", response_model=TransactionDetailOut)
async def get_transaction(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await transaction_service.get_transaction_detail(
        db=db,
        user_id=current_user.id,
        txn_id=transaction_id,
    )


@router.patch("/{transaction_id}", response_model=TransactionDetailOut)
async def update_transaction(
    transaction_id: str,
    payload: TransactionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await transaction_service.update_transaction(
        db=db,
        user_id=current_user.id,
        txn_id=transaction_id,
        merchant=payload.merchant,
        category_id=payload.category_id,
        description=payload.description,
        amount_minor=payload.amount_minor,
        direction=payload.direction,
        txn_date=payload.txn_date,
        create_rule=payload.create_rule or False,
    )
    return await transaction_service.get_transaction_detail(
        db=db,
        user_id=current_user.id,
        txn_id=transaction_id,
    )


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await transaction_service.soft_delete_transaction(
        db=db,
        user_id=current_user.id,
        txn_id=transaction_id,
    )
    return None

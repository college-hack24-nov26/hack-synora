from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.models import User
from app.schemas.budget import BudgetCreate, BudgetUpdate, BudgetResponse
from app.services import budget_service

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.get("", response_model=List[BudgetResponse])
async def list_budgets(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await budget_service.list_budgets(db, current_user.id)


@router.post("", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
async def create_budget(
    req: BudgetCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await budget_service.create_budget(db, current_user.id, req)


@router.get("/{budget_id}", response_model=BudgetResponse)
async def get_budget(
    budget_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await budget_service.get_budget(db, current_user.id, budget_id)


@router.patch("/{budget_id}", response_model=BudgetResponse)
async def update_budget(
    budget_id: str,
    req: BudgetUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await budget_service.update_budget(db, current_user.id, budget_id, req)


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(
    budget_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await budget_service.delete_budget(db, current_user.id, budget_id)
    return None


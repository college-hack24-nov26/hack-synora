import uuid
from typing import List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_owned_or_404
from app.core.errors import ConflictException, NotFoundException
from app.models.models import Budget, Category, AuditLog
from app.schemas.budget import BudgetCreate, BudgetUpdate


async def list_budgets(db: AsyncSession, user_id: str) -> List[Budget]:
    stmt = select(Budget).where(Budget.user_id == user_id).order_by(Budget.month.desc())
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def create_budget(db: AsyncSession, user_id: str, req: BudgetCreate) -> Budget:
    # Ensure category belongs to user or is system default
    await get_owned_or_404(db, Category, req.category_id, user_id, allow_system_read=True)

    # Check for duplicate
    dup_stmt = select(Budget).where(
        and_(
            Budget.user_id == user_id,
            Budget.category_id == req.category_id,
            Budget.month == req.month,
        )
    )
    dup = (await db.execute(dup_stmt)).scalar_one_or_none()
    if dup:
        raise ConflictException(f"Budget for category in month '{req.month}' already exists")

    budget = Budget(
        id=str(uuid.uuid4()),
        user_id=user_id,
        category_id=req.category_id,
        month=req.month,
        limit_minor=req.limit_minor,
    )
    db.add(budget)

    audit = AuditLog(
        id=str(uuid.uuid4()),
        user_id=user_id,
        action="BUDGET_CREATED",
        entity="budget",
        entity_id=budget.id,
        meta_data={"month": budget.month, "limit_minor": budget.limit_minor},
    )
    db.add(audit)

    await db.commit()
    await db.refresh(budget)
    return budget


async def get_budget(db: AsyncSession, user_id: str, budget_id: str) -> Budget:
    return await get_owned_or_404(db, Budget, budget_id, user_id)


async def update_budget(db: AsyncSession, user_id: str, budget_id: str, req: BudgetUpdate) -> Budget:
    budget = await get_owned_or_404(db, Budget, budget_id, user_id)
    budget.limit_minor = req.limit_minor
    await db.commit()
    await db.refresh(budget)
    return budget


async def delete_budget(db: AsyncSession, user_id: str, budget_id: str) -> None:
    budget = await get_owned_or_404(db, Budget, budget_id, user_id)
    await db.delete(budget)
    await db.commit()


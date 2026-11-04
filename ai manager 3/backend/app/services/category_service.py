import uuid
from typing import List, Optional
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_owned_or_404
from app.core.errors import NotFoundException, ForbiddenException, ConflictException
from app.models.models import Category, AuditLog
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryResponse


async def get_categories(db: AsyncSession, user_id: str) -> List[Category]:
    # Returns both system defaults (user_id IS NULL) and user's custom categories
    stmt = select(Category).where(
        or_(Category.user_id.is_(None), Category.user_id == user_id)
    ).order_by(Category.name.asc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_category(db: AsyncSession, user_id: str, req: CategoryCreate) -> Category:
    # Check if category with same name exists for this user or system
    stmt = select(Category).where(
        and_(
            Category.name.ilike(req.name.strip()),
            or_(Category.user_id.is_(None), Category.user_id == user_id),
        )
    )
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise ConflictException(f"Category '{req.name}' already exists")

    category = Category(
        id=str(uuid.uuid4()),
        user_id=user_id,
        name=req.name.strip(),
        parent_id=req.parent_id,
        icon=req.icon or "tag",
        color=req.color or "#6b7280",
        is_income=req.is_income,
    )
    db.add(category)

    audit = AuditLog(
        id=str(uuid.uuid4()),
        user_id=user_id,
        action="CATEGORY_CREATED",
        entity="category",
        entity_id=category.id,
        meta_data={"name": category.name},
    )
    db.add(audit)

    await db.commit()
    await db.refresh(category)
    return category


async def get_category_by_id(db: AsyncSession, user_id: str, category_id: str) -> Category:
    return await get_owned_or_404(db, Category, category_id, user_id, allow_system_read=True)


async def update_category(db: AsyncSession, user_id: str, category_id: str, req: CategoryUpdate) -> Category:
    stmt = select(Category).where(Category.id == category_id)
    result = await db.execute(stmt)
    category = result.scalar_one_or_none()

    if not category:
        raise NotFoundException("Category not found")

    if category.user_id is None:
        raise ForbiddenException("System default categories cannot be modified")

    if category.user_id != user_id:
        # Cross-user modification returns 404 to prevent ID probing
        raise NotFoundException("Category not found")

    if req.name is not None:
        category.name = req.name.strip()
    if req.parent_id is not None:
        category.parent_id = req.parent_id
    if req.icon is not None:
        category.icon = req.icon
    if req.color is not None:
        category.color = req.color
    if req.is_income is not None:
        category.is_income = req.is_income

    await db.commit()
    await db.refresh(category)
    return category


async def delete_category(db: AsyncSession, user_id: str, category_id: str) -> None:
    stmt = select(Category).where(Category.id == category_id)
    result = await db.execute(stmt)
    category = result.scalar_one_or_none()

    if not category:
        raise NotFoundException("Category not found")

    if category.user_id is None:
        raise ForbiddenException("System default categories cannot be deleted")

    if category.user_id != user_id:
        # Cross-user deletion returns 404 to prevent ID probing
        raise NotFoundException("Category not found")

    await db.delete(category)
    await db.commit()


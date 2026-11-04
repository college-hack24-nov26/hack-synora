import uuid
from typing import List, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import Category

DEFAULT_CATEGORIES: List[Dict[str, Any]] = [
    # Expenses
    {"name": "Food & Dining", "icon": "utensils", "color": "#f97316", "is_income": False},
    {"name": "Groceries", "icon": "shopping-cart", "color": "#10b981", "is_income": False},
    {"name": "Transport", "icon": "car", "color": "#3b82f6", "is_income": False},
    {"name": "Fuel", "icon": "fuel", "color": "#ef4444", "is_income": False},
    {"name": "Shopping", "icon": "shopping-bag", "color": "#ec4899", "is_income": False},
    {"name": "Bills & Utilities", "icon": "zap", "color": "#eab308", "is_income": False},
    {"name": "Rent", "icon": "home", "color": "#8b5cf6", "is_income": False},
    {"name": "EMI/Loans", "icon": "landmark", "color": "#6366f1", "is_income": False},
    {"name": "Entertainment", "icon": "film", "color": "#a855f7", "is_income": False},
    {"name": "Health", "icon": "heart-pulse", "color": "#14b8a6", "is_income": False},
    {"name": "Education", "icon": "graduation-cap", "color": "#06b6d4", "is_income": False},
    {"name": "Travel", "icon": "plane", "color": "#0ea5e9", "is_income": False},
    {"name": "Investments", "icon": "trending-up", "color": "#22c55e", "is_income": False},
    {"name": "Insurance", "icon": "shield-check", "color": "#64748b", "is_income": False},
    {"name": "Subscriptions", "icon": "repeat", "color": "#f43f5e", "is_income": False},
    {"name": "Transfers", "icon": "arrow-left-right", "color": "#94a3b8", "is_income": False},
    {"name": "Cash Withdrawal", "icon": "banknote", "color": "#78716c", "is_income": False},
    {"name": "Uncategorized", "icon": "help-circle", "color": "#9ca3af", "is_income": False},
    # Income
    {"name": "Salary", "icon": "briefcase", "color": "#16a34a", "is_income": True},
    {"name": "Other Income", "icon": "wallet", "color": "#059669", "is_income": True},
]


async def seed_default_categories(db: AsyncSession) -> None:
    """Seeds default categories if they do not exist."""
    for cat_data in DEFAULT_CATEGORIES:
        stmt = select(Category).where(Category.user_id.is_(None), Category.name == cat_data["name"])
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        if not existing:
            category = Category(
                id=str(uuid.uuid4()),
                user_id=None,  # System default category
                name=cat_data["name"],
                icon=cat_data.get("icon"),
                color=cat_data.get("color"),
                is_income=cat_data.get("is_income", False),
            )
            db.add(category)
    await db.commit()


from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import Transaction, Category, Account


async def get_analytics_summary(db: AsyncSession, user_id: str) -> Dict[str, Any]:
    # Sum credits
    credit_stmt = select(func.coalesce(func.sum(Transaction.amount_minor), 0)).where(
        and_(
            Transaction.user_id == user_id,
            Transaction.direction == "credit",
            Transaction.deleted_at.is_(None),
        )
    )
    debit_stmt = select(func.coalesce(func.sum(Transaction.amount_minor), 0)).where(
        and_(
            Transaction.user_id == user_id,
            Transaction.direction == "debit",
            Transaction.deleted_at.is_(None),
        )
    )
    count_stmt = select(func.count(Transaction.id)).where(
        and_(Transaction.user_id == user_id, Transaction.deleted_at.is_(None))
    )

    total_income_minor = (await db.execute(credit_stmt)).scalar_one()
    total_expense_minor = (await db.execute(debit_stmt)).scalar_one()
    total_txns = (await db.execute(count_stmt)).scalar_one()

    net_savings_minor = total_income_minor - total_expense_minor

    return {
        "total_income_minor": total_income_minor,
        "total_expense_minor": total_expense_minor,
        "net_savings_minor": net_savings_minor,
        "transaction_count": total_txns,
    }


async def get_spending_by_category(db: AsyncSession, user_id: str) -> List[Dict[str, Any]]:
    stmt = (
        select(
            Category.name,
            Category.color,
            func.sum(Transaction.amount_minor).label("total_minor"),
        )
        .join(Transaction, Transaction.category_id == Category.id)
        .where(
            and_(
                Transaction.user_id == user_id,
                Transaction.direction == "debit",
                Transaction.deleted_at.is_(None),
            )
        )
        .group_by(Category.name, Category.color)
        .order_by(func.sum(Transaction.amount_minor).desc())
    )

    res = await db.execute(stmt)
    rows = res.all()

    total_debit = sum(r[2] for r in rows) if rows else 0

    results = []
    for name, color, minor in rows:
        results.append({
            "name": name,
            "color": color or "#6b7280",
            "total_minor": minor,
            "percentage": round((minor / total_debit) * 100, 1) if total_debit > 0 else 0,
        })

    return results


import uuid
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_owned_or_404
from app.models.models import MerchantRule, Category, AuditLog
from app.schemas.merchant_rule import MerchantRuleCreate, MerchantRuleUpdate


async def list_merchant_rules(db: AsyncSession, user_id: str) -> List[MerchantRule]:
    stmt = (
        select(MerchantRule)
        .where(MerchantRule.user_id == user_id)
        .order_by(MerchantRule.priority.desc(), MerchantRule.created_at.desc())
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def create_merchant_rule(db: AsyncSession, user_id: str, req: MerchantRuleCreate) -> MerchantRule:
    # Ensure category belongs to user or is system default
    await get_owned_or_404(db, Category, req.category_id, user_id, allow_system_read=True)

    rule = MerchantRule(
        id=str(uuid.uuid4()),
        user_id=user_id,
        pattern=req.pattern.strip(),
        category_id=req.category_id,
        priority=req.priority,
    )
    db.add(rule)

    audit = AuditLog(
        id=str(uuid.uuid4()),
        user_id=user_id,
        action="MERCHANT_RULE_CREATED",
        entity="merchant_rule",
        entity_id=rule.id,
        meta_data={"pattern": rule.pattern},
    )
    db.add(audit)

    await db.commit()
    await db.refresh(rule)
    return rule


async def get_merchant_rule(db: AsyncSession, user_id: str, rule_id: str) -> MerchantRule:
    return await get_owned_or_404(db, MerchantRule, rule_id, user_id)


async def update_merchant_rule(
    db: AsyncSession, user_id: str, rule_id: str, req: MerchantRuleUpdate
) -> MerchantRule:
    rule = await get_owned_or_404(db, MerchantRule, rule_id, user_id)

    if req.category_id is not None:
        await get_owned_or_404(db, Category, req.category_id, user_id, allow_system_read=True)
        rule.category_id = req.category_id
    if req.pattern is not None:
        rule.pattern = req.pattern.strip()
    if req.priority is not None:
        rule.priority = req.priority

    await db.commit()
    await db.refresh(rule)
    return rule


async def delete_merchant_rule(db: AsyncSession, user_id: str, rule_id: str) -> None:
    rule = await get_owned_or_404(db, MerchantRule, rule_id, user_id)
    await db.delete(rule)
    await db.commit()


from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.models import User
from app.schemas.merchant_rule import (
    MerchantRuleCreate,
    MerchantRuleUpdate,
    MerchantRuleResponse,
)
from app.services import merchant_rule_service

router = APIRouter(prefix="/merchant-rules", tags=["merchant-rules"])


@router.get("", response_model=List[MerchantRuleResponse])
async def list_merchant_rules(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await merchant_rule_service.list_merchant_rules(db, current_user.id)


@router.post("", response_model=MerchantRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_merchant_rule(
    req: MerchantRuleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await merchant_rule_service.create_merchant_rule(db, current_user.id, req)


@router.get("/{rule_id}", response_model=MerchantRuleResponse)
async def get_merchant_rule(
    rule_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await merchant_rule_service.get_merchant_rule(db, current_user.id, rule_id)


@router.patch("/{rule_id}", response_model=MerchantRuleResponse)
async def update_merchant_rule(
    rule_id: str,
    req: MerchantRuleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await merchant_rule_service.update_merchant_rule(db, current_user.id, rule_id, req)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_merchant_rule(
    rule_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await merchant_rule_service.delete_merchant_rule(db, current_user.id, rule_id)
    return None


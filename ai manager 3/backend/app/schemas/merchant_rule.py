from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class MerchantRuleCreate(BaseModel):
    pattern: str = Field(..., min_length=1, max_length=255)
    category_id: str
    priority: int = 0


class MerchantRuleUpdate(BaseModel):
    pattern: Optional[str] = Field(None, min_length=1, max_length=255)
    category_id: Optional[str] = None
    priority: Optional[int] = None


class MerchantRuleResponse(BaseModel):
    id: str
    user_id: str
    pattern: str
    category_id: str
    priority: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


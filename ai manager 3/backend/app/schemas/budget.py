from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class BudgetCreate(BaseModel):
    category_id: str
    month: str = Field(..., pattern=r"^\d{4}-\d{2}$", description="Month in YYYY-MM format")
    limit_minor: int = Field(..., gt=0, description="Monthly spending limit in minor units (paise)")


class BudgetUpdate(BaseModel):
    limit_minor: int = Field(..., gt=0, description="Updated limit in minor units")


class BudgetResponse(BaseModel):
    id: str
    user_id: str
    category_id: str
    month: str
    limit_minor: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


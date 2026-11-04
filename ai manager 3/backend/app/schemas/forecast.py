from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ForecastCreate(BaseModel):
    target_month: str = Field(..., pattern=r"^\d{4}-\d{2}$", description="Month in YYYY-MM format")
    category_id: Optional[str] = None
    predicted_minor: int = Field(..., gt=0)
    lower_bound_minor: int = Field(..., ge=0)
    upper_bound_minor: int = Field(..., ge=0)
    model_version: Optional[str] = "v1-stat"


class ForecastResponse(BaseModel):
    id: str
    user_id: str
    target_month: str
    category_id: Optional[str] = None
    predicted_minor: int
    lower_bound_minor: int
    upper_bound_minor: int
    model_version: str
    created_at: datetime

    class Config:
        from_attributes = True


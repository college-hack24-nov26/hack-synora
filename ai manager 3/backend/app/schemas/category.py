from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    parent_id: Optional[str] = None
    icon: Optional[str] = Field("tag", max_length=50)
    color: Optional[str] = Field("#6b7280", max_length=20)
    is_income: bool = False


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    parent_id: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    is_income: Optional[bool] = None


class CategoryResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    name: str
    parent_id: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    is_income: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

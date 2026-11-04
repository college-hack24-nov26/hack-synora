from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class TransactionCategoryOut(BaseModel):
    id: Optional[str] = None
    name: str = "Uncategorized"
    icon: Optional[str] = "tag"
    color: Optional[str] = "#6b7280"

    class Config:
        from_attributes = True


class TransactionOut(BaseModel):
    id: str
    merchant: str
    txn_date: datetime
    category: Optional[TransactionCategoryOut] = None
    amount_minor: int
    direction: Literal["debit", "credit"]
    currency: str = "INR"
    source: str
    category_source: Optional[str] = "rule"
    category_confidence: Optional[float] = 1.0
    needs_review: Optional[bool] = False
    account_id: Optional[str] = None
    account_name: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TransactionDetailOut(TransactionOut):
    user_id: str
    merchant_raw: Optional[str] = None
    merchant_normalized: Optional[str] = None
    category_id: Optional[str] = None
    category_source: Optional[str] = "rule"
    category_confidence: Optional[float] = 1.0
    needs_review: Optional[bool] = False
    import_id: Optional[str] = None
    dedupe_hash: Optional[str] = None
    updated_at: Optional[datetime] = None


class TransactionListResponse(BaseModel):
    items: List[TransactionOut]
    total: int
    page: int
    limit: int
    total_pages: int


class CategorySummaryItem(BaseModel):
    category_id: Optional[str] = None
    name: str
    icon: Optional[str] = "tag"
    color: Optional[str] = "#6b7280"
    total_minor: int
    count: int
    percentage: float


class TransactionSummaryResponse(BaseModel):
    total_spent_minor: int
    total_income_minor: int
    transaction_count: int
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    top_categories: List[CategorySummaryItem]


class TransactionCreate(BaseModel):
    account_id: str
    amount_minor: int = Field(..., gt=0, description="Amount in minor units (paise)")
    direction: Literal["debit", "credit"]
    merchant: str = Field(..., min_length=1, max_length=255)
    category_id: Optional[str] = None
    txn_date: Optional[datetime] = None
    description: Optional[str] = None


class TransactionUpdate(BaseModel):
    merchant: Optional[str] = Field(None, min_length=1, max_length=255)
    category_id: Optional[str] = None
    description: Optional[str] = None
    amount_minor: Optional[int] = Field(None, gt=0)
    direction: Optional[Literal["debit", "credit"]] = None
    txn_date: Optional[datetime] = None
    create_rule: Optional[bool] = False


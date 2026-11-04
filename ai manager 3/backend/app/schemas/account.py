from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field, ConfigDict

AccountType = Literal["savings", "current", "credit_card", "wallet", "cash"]


class AccountCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: AccountType
    last4: Optional[str] = Field(None, min_length=4, max_length=4, pattern=r"^\d{4}$")
    opening_balance_minor: int = Field(0, description="Opening balance in paise (integer minor units)")


class AccountUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    type: Optional[AccountType] = None
    last4: Optional[str] = Field(None, min_length=4, max_length=4, pattern=r"^\d{4}$")
    opening_balance_minor: Optional[int] = None


class AccountResponse(BaseModel):
    id: str
    user_id: str
    name: str
    type: str
    last4: Optional[str] = None
    opening_balance_minor: int
    current_balance_minor: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

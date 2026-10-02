from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.models.expense import ExpenseStatus

MAX_EXPENSE_AMOUNT = 1_000_000.0  # sanity cap; adjust to business rules


class ExpenseCreate(BaseModel):
    category: str = Field(min_length=1, max_length=50)
    amount: float = Field(gt=0)
    description: str = Field(default="", max_length=1000)

    @field_validator("amount")
    @classmethod
    def amount_within_bounds(cls, v: float) -> float:
        if v > MAX_EXPENSE_AMOUNT:
            raise ValueError(f"amount cannot exceed {MAX_EXPENSE_AMOUNT}")
        return round(v, 2)


class ExpenseUpdate(BaseModel):
    category: Optional[str] = Field(default=None, min_length=1, max_length=50)
    amount: Optional[float] = Field(default=None, gt=0, le=MAX_EXPENSE_AMOUNT)
    description: Optional[str] = Field(default=None, max_length=1000)


class ExpenseReview(BaseModel):
    approve: bool
    comment: str = Field(default="", max_length=1000)


class ExpenseOut(BaseModel):
    id: int
    owner_id: int
    category: str
    amount: float
    description: str
    status: ExpenseStatus
    reviewer_id: Optional[int]
    reviewer_comment: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

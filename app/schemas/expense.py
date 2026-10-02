from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.models.expense import ExpenseStatus

MAX_EXPENSE_AMOUNT = 1_000_000.0


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


class AuditLogOut(BaseModel):
    id: int
    expense_id: int
    actor_id: int
    action: str
    from_status: Optional[str]
    to_status: Optional[str]
    comment: str
    timestamp: datetime

    class Config:
        from_attributes = True


class ExpenseOut(BaseModel):
    id: int
    owner_id: int
    owner_name: Optional[str] = None
    category: str
    amount: float
    description: str
    status: ExpenseStatus
    reviewer_id: Optional[int]
    reviewer_comment: str
    policy_flagged: bool
    policy_limit: float
    policy_flag_reason: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CategoryTotal(BaseModel):
    category: str
    total: float
    count: int


class SpenderTotal(BaseModel):
    owner_id: int
    full_name: str
    total: float
    count: int


class MonthTotal(BaseModel):
    month: str  # "YYYY-MM"
    label: str  # "Sep"
    total: float
    count: int


class ExpenseSummary(BaseModel):
    """Business-wide spending picture for managers and admins.

    "Spend" (total_requested, by_category, top_spenders, by_month) counts
    submitted, approved and reimbursed expenses. Drafts were never sent to
    anyone and rejected expenses will not be paid, so neither is spend.
    """

    total_count: int
    total_requested: float
    average_expense: float
    approval_rate: Optional[float]  # % of decided expenses that were approved
    pending_count: int
    pending_amount: float
    awaiting_payment_count: int
    awaiting_payment_amount: float
    reimbursed_count: int
    reimbursed_amount: float
    rejected_count: int
    flagged_count: int
    by_category: list[CategoryTotal]
    top_spenders: list[SpenderTotal]
    by_month: list[MonthTotal]

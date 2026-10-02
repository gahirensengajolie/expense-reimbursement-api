import enum
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Float, Enum, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class ExpenseStatus(str, enum.Enum):
    draft = "draft"
    submitted = "submitted"
    approved = "approved"
    rejected = "rejected"
    reimbursed = "reimbursed"


# Allowed transitions: guards against illegal state jumps (e.g. draft -> reimbursed)
ALLOWED_TRANSITIONS = {
    ExpenseStatus.draft: {ExpenseStatus.submitted},
    ExpenseStatus.submitted: {ExpenseStatus.approved, ExpenseStatus.rejected},
    ExpenseStatus.approved: {ExpenseStatus.reimbursed},
    ExpenseStatus.rejected: {ExpenseStatus.draft},
    ExpenseStatus.reimbursed: set(),
}


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    category = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(Text, default="")
    status = Column(Enum(ExpenseStatus), default=ExpenseStatus.draft, nullable=False)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewer_comment = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    owner = relationship("User", back_populates="expenses", foreign_keys=[owner_id])


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    expense_id = Column(Integer, ForeignKey("expenses.id"), nullable=False, index=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String, nullable=False)  # e.g. "submitted", "approved", "rejected"
    from_status = Column(String, nullable=True)
    to_status = Column(String, nullable=True)
    comment = Column(Text, default="")
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

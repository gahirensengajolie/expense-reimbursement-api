from typing import Optional, List

from sqlalchemy.orm import Session

from app.models.expense import Expense, ExpenseStatus, AuditLog


class ExpenseRepository:
    """
    Owns all direct SQLAlchemy queries for Expense/AuditLog. Contains no
    authorization or workflow logic -- that belongs in ExpenseService.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, expense_id: int) -> Optional[Expense]:
        return self.db.query(Expense).filter(Expense.id == expense_id).first()

    def list(
        self,
        owner_id: Optional[int] = None,
        status: Optional[ExpenseStatus] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Expense]:
        query = self.db.query(Expense)
        if owner_id is not None:
            query = query.filter(Expense.owner_id == owner_id)
        if status is not None:
            query = query.filter(Expense.status == status)
        return query.order_by(Expense.created_at.desc()).offset(offset).limit(limit).all()

    def create(self, owner_id: int, category: str, amount: float, description: str) -> Expense:
        expense = Expense(
            owner_id=owner_id,
            category=category,
            amount=amount,
            description=description,
        )
        self.db.add(expense)
        self.db.commit()
        self.db.refresh(expense)
        return expense

    def update_fields(self, expense: Expense, fields: dict) -> Expense:
        for key, value in fields.items():
            setattr(expense, key, value)
        self.db.commit()
        self.db.refresh(expense)
        return expense

    def set_status(self, expense: Expense, new_status: ExpenseStatus) -> Expense:
        expense.status = new_status
        self.db.commit()
        self.db.refresh(expense)
        return expense

    def set_review(self, expense: Expense, reviewer_id: int, comment: str) -> Expense:
        expense.reviewer_id = reviewer_id
        expense.reviewer_comment = comment
        self.db.commit()
        self.db.refresh(expense)
        return expense

    def delete(self, expense: Expense) -> None:
        # Remove dependent audit rows first -- draft expenses only ever have
        # a single "created" audit entry, so nothing meaningful is lost.
        self.db.query(AuditLog).filter(AuditLog.expense_id == expense.id).delete()
        self.db.delete(expense)
        self.db.commit()

    def add_audit_log(
        self,
        expense_id: int,
        actor_id: int,
        action: str,
        from_status: Optional[ExpenseStatus],
        to_status: Optional[ExpenseStatus],
        comment: str = "",
    ) -> AuditLog:
        entry = AuditLog(
            expense_id=expense_id,
            actor_id=actor_id,
            action=action,
            from_status=from_status.value if from_status else None,
            to_status=to_status.value if to_status else None,
            comment=comment,
        )
        self.db.add(entry)
        self.db.commit()
        return entry

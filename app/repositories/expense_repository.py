import builtins
from typing import Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.expense import AuditLog, Expense, ExpenseStatus
from app.models.user import User


class ExpenseRepository:
    """
    Owns all direct SQLAlchemy queries for Expense/AuditLog. Contains no
    authorization or workflow logic -- that belongs in ExpenseService.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, expense_id: int) -> Optional[Expense]:
        return (
            self.db.query(Expense)
            .options(joinedload(Expense.owner))
            .filter(Expense.id == expense_id)
            .first()
        )

    @staticmethod
    def _scoped(
        query,
        owner_id: Optional[int],
        status: Optional[ExpenseStatus],
        exclude_drafts: bool,
        team_manager_id: Optional[int],
    ):
        """Shared visibility filters, applied in SQL so out-of-scope rows never load.

        owner_id         -> only that person's expenses (employees)
        exclude_drafts   -> drafts are private to their owner (reviewers never see them)
        team_manager_id  -> a manager's view: their direct reports plus unassigned employees
        """
        if owner_id is not None:
            query = query.filter(Expense.owner_id == owner_id)
        if status is not None:
            query = query.filter(Expense.status == status)
        if exclude_drafts:
            query = query.filter(Expense.status != ExpenseStatus.draft)
        if team_manager_id is not None:
            query = query.join(User, User.id == Expense.owner_id).filter(
                or_(User.manager_id == team_manager_id, User.manager_id.is_(None))
            )
        return query

    def list(
        self,
        owner_id: Optional[int] = None,
        status: Optional[ExpenseStatus] = None,
        limit: int = 20,
        offset: int = 0,
        exclude_drafts: bool = False,
        team_manager_id: Optional[int] = None,
    ) -> list[Expense]:
        query = self.db.query(Expense).options(joinedload(Expense.owner))
        query = self._scoped(query, owner_id, status, exclude_drafts, team_manager_id)
        return query.order_by(Expense.created_at.desc()).offset(offset).limit(limit).all()

    def count(
        self,
        owner_id: Optional[int] = None,
        status: Optional[ExpenseStatus] = None,
        exclude_drafts: bool = False,
        team_manager_id: Optional[int] = None,
    ) -> int:
        query = self.db.query(func.count(Expense.id))
        query = self._scoped(query, owner_id, status, exclude_drafts, team_manager_id)
        return query.scalar() or 0

    def list_submitted_ever(self, team_manager_id: Optional[int] = None) -> builtins.list[Expense]:
        """Every expense that has left draft (submitted, decided or paid)."""
        query = self.db.query(Expense).options(joinedload(Expense.owner))
        query = self._scoped(query, None, None, True, team_manager_id)
        return query.all()

    def list_audit_logs(self, expense_id: int) -> builtins.list[AuditLog]:
        return (
            self.db.query(AuditLog)
            .filter(AuditLog.expense_id == expense_id)
            .order_by(AuditLog.timestamp.asc(), AuditLog.id.asc())
            .all()
        )

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

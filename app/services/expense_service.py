from typing import List, Optional

from sqlalchemy.orm import Session

from app.exceptions import NotFoundError, ForbiddenError, ConflictError
from app.models.expense import Expense, ExpenseStatus, ALLOWED_TRANSITIONS
from app.models.user import User, RoleEnum
from app.repositories.expense_repository import ExpenseRepository


class ExpenseService:
    def __init__(self, db: Session):
        self.repo = ExpenseRepository(db)

    # ---- internal helpers ----------------------------------------------

    def _get_visible_or_404(self, expense_id: int, user: User) -> Expense:
        """
        Single authorization chokepoint for "can this user see this
        expense at all". Every read/write path goes through this so the
        ownership rule can't drift between endpoints (the classic source
        of IDOR bugs).
        """
        expense = self.repo.get_by_id(expense_id)
        if not expense:
            raise NotFoundError("Expense not found")

        is_owner = expense.owner_id == user.id
        is_privileged = user.role in (RoleEnum.manager, RoleEnum.admin)

        if not (is_owner or is_privileged):
            # 404, not 403: don't confirm the resource exists to someone
            # with no business knowing about it.
            raise NotFoundError("Expense not found")

        return expense

    def _transition(
        self,
        expense: Expense,
        actor: User,
        new_status: ExpenseStatus,
        action: str,
        comment: str = "",
    ) -> Expense:
        if new_status not in ALLOWED_TRANSITIONS.get(expense.status, set()):
            raise ConflictError(
                f"Cannot move expense from '{expense.status.value}' to '{new_status.value}'"
            )
        old_status = expense.status
        expense = self.repo.set_status(expense, new_status)
        self.repo.add_audit_log(expense.id, actor.id, action, old_status, new_status, comment)
        return expense

    # ---- CRUD ------------------------------------------------------------

    def create(self, user: User, category: str, amount: float, description: str) -> Expense:
        expense = self.repo.create(user.id, category, amount, description)
        self.repo.add_audit_log(expense.id, user.id, "created", None, ExpenseStatus.draft)
        return expense

    def get(self, expense_id: int, user: User) -> Expense:
        return self._get_visible_or_404(expense_id, user)

    def list(
        self,
        user: User,
        status: Optional[ExpenseStatus] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Expense]:
        # Employees only ever see their own; managers/admins see everyone's.
        # Scoping happens at the query level (in the repository), not by
        # filtering an already-loaded list, so unscoped data is never even
        # pulled into memory.
        owner_id = user.id if user.role == RoleEnum.employee else None
        return self.repo.list(owner_id=owner_id, status=status, limit=limit, offset=offset)

    def update(self, expense_id: int, user: User, fields: dict) -> Expense:
        expense = self._get_visible_or_404(expense_id, user)

        if expense.owner_id != user.id:
            raise ForbiddenError("Only the owner can edit this expense")
        if expense.status != ExpenseStatus.draft:
            raise ConflictError("Only draft expenses can be edited")

        return self.repo.update_fields(expense, fields)

    def delete(self, expense_id: int, user: User) -> None:
        """
        Real delete -- but scoped to drafts only. Once an expense is
        submitted it becomes part of the approval/audit trail and must
        not disappear (compliance concern in any real expense system).
        Draft expenses were never part of that trail, so removing them
        outright (plus their single "created" audit row) is safe.
        """
        expense = self._get_visible_or_404(expense_id, user)

        if expense.owner_id != user.id:
            raise ForbiddenError("Only the owner can delete this expense")
        if expense.status != ExpenseStatus.draft:
            raise ConflictError(
                "Only draft expenses can be deleted; submitted expenses must be tracked, not removed"
            )

        self.repo.delete(expense)

    # ---- workflow actions --------------------------------------------

    def submit(self, expense_id: int, user: User) -> Expense:
        expense = self._get_visible_or_404(expense_id, user)
        if expense.owner_id != user.id:
            raise ForbiddenError("Only the owner can submit this expense")
        return self._transition(expense, user, ExpenseStatus.submitted, "submitted")

    def review(self, expense_id: int, reviewer: User, approve: bool, comment: str) -> Expense:
        expense = self.repo.get_by_id(expense_id)
        if not expense:
            raise NotFoundError("Expense not found")

        # Role-gating happens at the router (require_roles), but the
        # self-approval loophole is a business rule, so it lives here.
        if expense.owner_id == reviewer.id:
            raise ForbiddenError("You cannot review your own expense")

        new_status = ExpenseStatus.approved if approve else ExpenseStatus.rejected
        action = "approved" if approve else "rejected"

        expense = self._transition(expense, reviewer, new_status, action, comment)
        return self.repo.set_review(expense, reviewer.id, comment)

    def reimburse(self, expense_id: int, admin: User) -> Expense:
        expense = self.repo.get_by_id(expense_id)
        if not expense:
            raise NotFoundError("Expense not found")
        return self._transition(expense, admin, ExpenseStatus.reimbursed, "reimbursed")

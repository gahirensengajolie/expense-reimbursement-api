from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.core.policies import evaluate_spending_policy
from app.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.expense import ALLOWED_TRANSITIONS, Expense, ExpenseStatus
from app.models.user import RoleEnum, User
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
        flagged, _, reason = evaluate_spending_policy(category, amount)
        if flagged:
            self.repo.add_audit_log(
                expense.id,
                user.id,
                "policy_flagged",
                ExpenseStatus.draft,
                ExpenseStatus.draft,
                reason,
            )
        return expense

    def get(self, expense_id: int, user: User) -> Expense:
        return self._get_visible_or_404(expense_id, user)

    def list(
        self,
        user: User,
        status: Optional[ExpenseStatus] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Expense]:
        # Employees only ever see their own; managers/admins see everyone's.
        # Scoping happens at the query level (in the repository), not by
        # filtering an already-loaded list, so unscoped data is never even
        # pulled into memory.
        owner_id = user.id if user.role == RoleEnum.employee else None
        return self.repo.list(owner_id=owner_id, status=status, limit=limit, offset=offset)

    def count(self, user: User, status: Optional[ExpenseStatus] = None) -> int:
        owner_id = user.id if user.role == RoleEnum.employee else None
        return self.repo.count(owner_id=owner_id, status=status)

    def audit_history(self, expense_id: int, user: User):
        self._get_visible_or_404(expense_id, user)
        return self.repo.list_audit_logs(expense_id)

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

    def resubmit(self, expense_id: int, user: User) -> Expense:
        expense = self._get_visible_or_404(expense_id, user)
        if expense.owner_id != user.id:
            raise ForbiddenError("Only the owner can resubmit this expense")
        if expense.status != ExpenseStatus.rejected:
            raise ConflictError("Only rejected expenses can be resubmitted")
        self._transition(expense, user, ExpenseStatus.draft, "returned_to_draft")
        return self._transition(expense, user, ExpenseStatus.submitted, "resubmitted")

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

    # ---- analytics -----------------------------------------------------

    def summary(self, months: int = 6) -> dict:
        """Aggregate figures for the manager/admin dashboard.

        Role-gating happens at the router. Aggregation is done in Python so
        it behaves the same on SQLite and Postgres; if the table ever gets
        very large, move these into SQL GROUP BY queries.
        """
        rows = self.repo.list_submitted_ever()
        S = ExpenseStatus

        def bucket(status):
            items = [e for e in rows if e.status == status]
            return len(items), round(sum(e.amount for e in items), 2)

        pending_count, pending_amount = bucket(S.submitted)
        awaiting_count, awaiting_amount = bucket(S.approved)
        paid_count, paid_amount = bucket(S.reimbursed)
        rejected_count, _ = bucket(S.rejected)

        spend = [e for e in rows if e.status != S.rejected]
        total = round(sum(e.amount for e in spend), 2)
        decided = len(spend) - pending_count + rejected_count
        approved = awaiting_count + paid_count

        by_category = defaultdict(lambda: [0.0, 0])
        by_owner = defaultdict(lambda: [0.0, 0, ""])
        for e in spend:
            cat = by_category[e.category.strip().lower()]
            cat[0] += e.amount
            cat[1] += 1
            own = by_owner[e.owner_id]
            own[0] += e.amount
            own[1] += 1
            own[2] = e.owner_name or "Unknown"

        now = datetime.now(timezone.utc)
        keys = []
        y, m = now.year, now.month
        for _ in range(months):
            keys.append((y, m))
            m -= 1
            if m == 0:
                y, m = y - 1, 12
        keys.reverse()
        month_totals = {k: [0.0, 0] for k in keys}
        for e in spend:
            k = (e.created_at.year, e.created_at.month)
            if k in month_totals:
                month_totals[k][0] += e.amount
                month_totals[k][1] += 1

        return {
            "total_count": len(spend),
            "total_requested": total,
            "average_expense": round(total / len(spend), 2) if spend else 0.0,
            "approval_rate": round(approved / decided * 100, 1) if decided else None,
            "pending_count": pending_count,
            "pending_amount": pending_amount,
            "awaiting_payment_count": awaiting_count,
            "awaiting_payment_amount": awaiting_amount,
            "reimbursed_count": paid_count,
            "reimbursed_amount": paid_amount,
            "rejected_count": rejected_count,
            "flagged_count": sum(1 for e in rows if e.policy_flagged),
            "by_category": sorted(
                (
                    {"category": c, "total": round(v[0], 2), "count": v[1]}
                    for c, v in by_category.items()
                ),
                key=lambda r: r["total"],
                reverse=True,
            ),
            "top_spenders": sorted(
                (
                    {"owner_id": oid, "full_name": v[2], "total": round(v[0], 2), "count": v[1]}
                    for oid, v in by_owner.items()
                ),
                key=lambda r: r["total"],
                reverse=True,
            )[:5],
            "by_month": [
                {
                    "month": f"{y}-{m:02d}",
                    "label": datetime(y, m, 1).strftime("%b"),
                    "total": round(month_totals[(y, m)][0], 2),
                    "count": month_totals[(y, m)][1],
                }
                for (y, m) in keys
            ],
        }

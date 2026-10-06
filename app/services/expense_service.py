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

        if not (expense.owner_id == user.id or self._reviewer_can_see(expense, user)):
            # 404, not 403: don't confirm the resource exists to someone
            # with no business knowing about it.
            raise NotFoundError("Expense not found")

        return expense

    @staticmethod
    def _reviewer_can_see(expense: Expense, user: User) -> bool:
        """Reviewer visibility rules.

        * Drafts are private: only the owner ever sees them.
        * Admins see everything else.
        * Managers see their direct reports' expenses, plus those of employees
          who have not been assigned to any manager yet.
        """
        if user.role not in (RoleEnum.manager, RoleEnum.admin):
            return False
        if expense.status == ExpenseStatus.draft:
            return False
        if user.role == RoleEnum.admin:
            return True
        owner_manager_id = expense.owner.manager_id if expense.owner else None
        return owner_manager_id is None or owner_manager_id == user.id

    @staticmethod
    def _scope(user: User) -> dict:
        """The same rules as _reviewer_can_see, expressed as repository filters."""
        if user.role == RoleEnum.employee:
            return {"owner_id": user.id}
        if user.role == RoleEnum.manager:
            return {"exclude_drafts": True, "team_manager_id": user.id}
        return {"exclude_drafts": True}

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
        # Employees see their own; managers see their team; admins see all
        # submitted expenses. Scoping happens at the query level (in the
        # repository), not by filtering an already-loaded list, so unscoped
        # data is never even pulled into memory.
        return self.repo.list(status=status, limit=limit, offset=offset, **self._scope(user))

    def count(self, user: User, status: Optional[ExpenseStatus] = None) -> int:
        return self.repo.count(status=status, **self._scope(user))

    def counts(self, user: User) -> dict:
        """Cheap SQL counts for the menu badges (the page list is capped, these are not)."""
        return {
            "pending": self.count(user, ExpenseStatus.submitted),
            "payable": self.count(user, ExpenseStatus.approved),
        }

    def export_rows(self, user: User, status: Optional[ExpenseStatus] = None,
                    page_size: int = 500, max_rows: int = 20000) -> "list[Expense]":
        """Everything the user may see, fetched in pages, for the CSV export."""
        rows: list[Expense] = []
        while len(rows) < max_rows:
            batch = self.repo.list(status=status, limit=page_size, offset=len(rows), **self._scope(user))
            rows.extend(batch)
            if len(batch) < page_size:
                break
        return rows[:max_rows]

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
        # Same chokepoint as reads: a manager cannot act on another team's expense.
        expense = self._get_visible_or_404(expense_id, reviewer)

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

    def summary(self, user: User, months: int = 6) -> dict:
        """Aggregate figures for the manager/admin dashboard.

        Role-gating happens at the router. Aggregation is done in Python so
        it behaves the same on SQLite and Postgres; if the table ever gets
        very large, move these into SQL GROUP BY queries.
        """
        team = user.id if user.role == RoleEnum.manager else None
        rows = self.repo.list_submitted_ever(team_manager_id=team)
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

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.user import User, RoleEnum
from app.models.expense import ExpenseStatus
from app.schemas.expense import ExpenseCreate, ExpenseUpdate, ExpenseOut, ExpenseReview
from app.services.expense_service import ExpenseService

router = APIRouter(prefix="/expenses", tags=["expenses"])


@router.post("", response_model=ExpenseOut, status_code=status.HTTP_201_CREATED)
def create_expense(
    payload: ExpenseCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = ExpenseService(db)
    return service.create(user, payload.category, payload.amount, payload.description)


@router.get("", response_model=List[ExpenseOut])
def list_expenses(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    status_filter: Optional[ExpenseStatus] = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    service = ExpenseService(db)
    return service.list(user, status=status_filter, limit=limit, offset=offset)


@router.get("/{expense_id}", response_model=ExpenseOut)
def get_expense(expense_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    service = ExpenseService(db)
    return service.get(expense_id, user)


@router.patch("/{expense_id}", response_model=ExpenseOut)
def update_expense(
    expense_id: int,
    payload: ExpenseUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = ExpenseService(db)
    return service.update(expense_id, user, payload.model_dump(exclude_unset=True))


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(expense_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Deletes a DRAFT expense only. Once submitted, an expense enters the
    audit trail and must be tracked (rejected/withdrawn-back-to-draft),
    never silently removed.
    """
    service = ExpenseService(db)
    service.delete(expense_id, user)
    return None


@router.post("/{expense_id}/submit", response_model=ExpenseOut)
def submit_expense(expense_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    service = ExpenseService(db)
    return service.submit(expense_id, user)


@router.post("/{expense_id}/review", response_model=ExpenseOut)
def review_expense(
    expense_id: int,
    payload: ExpenseReview,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(RoleEnum.manager, RoleEnum.admin)),
):
    service = ExpenseService(db)
    return service.review(expense_id, user, payload.approve, payload.comment)


@router.post("/{expense_id}/reimburse", response_model=ExpenseOut)
def reimburse_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(RoleEnum.admin)),
):
    service = ExpenseService(db)
    return service.reimburse(expense_id, user)

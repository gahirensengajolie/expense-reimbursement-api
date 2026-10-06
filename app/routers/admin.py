from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.models.user import RoleEnum, User
from app.schemas.user import (
    AdminUserCreate,
    PasswordResetRequest,
    RoleUpdateRequest,
    UserOut,
    UserUpdate,
)
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin", tags=["admin"])

AdminOnly = require_roles(RoleEnum.admin)


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _: User = Depends(AdminOnly)):
    return AdminService(db).list_users()


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(
    payload: AdminUserCreate, db: Session = Depends(get_db), _: User = Depends(AdminOnly)
):
    """Create an account with a temporary password the person must change at first sign-in."""
    return AdminService(db).create_user(
        payload.email, payload.full_name, payload.role, payload.password, payload.manager_id
    )


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(AdminOnly),
):
    """Change name, role, manager assignment or enable/disable an account."""
    return AdminService(db).update_user(admin, user_id, payload.model_dump(exclude_unset=True))


@router.patch("/users/{user_id}/role", response_model=UserOut)
def update_role(
    user_id: int,
    payload: RoleUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(AdminOnly),
):
    return AdminService(db).update_role(admin, user_id, payload.role)


@router.post("/users/{user_id}/reset-password", response_model=UserOut)
def reset_password(
    user_id: int,
    payload: PasswordResetRequest,
    db: Session = Depends(get_db),
    _: User = Depends(AdminOnly),
):
    return AdminService(db).reset_password(user_id, payload.password)

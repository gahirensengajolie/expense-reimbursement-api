from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.models.user import RoleEnum, User
from app.schemas.user import RoleUpdateRequest, UserOut
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_roles(RoleEnum.admin))):
    service = AdminService(db)
    return service.list_users()


@router.patch("/users/{user_id}/role", response_model=UserOut)
def update_role(
    user_id: int,
    payload: RoleUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(RoleEnum.admin)),
):
    service = AdminService(db)
    return service.update_role(admin, user_id, payload.role)

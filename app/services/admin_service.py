from typing import Optional

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.exceptions import BadRequestError, NotFoundError
from app.models.user import RoleEnum, User
from app.repositories.user_repository import UserRepository


class AdminService:
    def __init__(self, db: Session):
        self.repo = UserRepository(db)

    def list_users(self) -> list[User]:
        return self.repo.list_all()

    # ---- helpers ---------------------------------------------------------

    def _get_or_404(self, user_id: int) -> User:
        user = self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        return user

    def _validated_manager_id(self, manager_id: Optional[int]) -> Optional[int]:
        if manager_id is None:
            return None
        manager = self.repo.get_by_id(manager_id)
        if not manager or manager.role != RoleEnum.manager or not manager.is_active:
            raise BadRequestError("Manager must be an active user with the manager role")
        return manager.id

    # ---- account management ------------------------------------------------

    def create_user(
        self,
        email: str,
        full_name: str,
        role: RoleEnum,
        password: str,
        manager_id: Optional[int] = None,
    ) -> User:
        if self.repo.get_by_email(email):
            raise BadRequestError("Email already registered")
        if manager_id is not None and role != RoleEnum.employee:
            raise BadRequestError("Only employees can be assigned to a manager")
        return self.repo.create(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
            role=role,
            manager_id=self._validated_manager_id(manager_id),
            must_change_password=True,
        )

    def update_user(self, admin: User, user_id: int, changes: dict) -> User:
        user = self._get_or_404(user_id)

        new_role = changes.get("role", user.role)
        if user.id == admin.id and (new_role != user.role or changes.get("is_active") is False):
            raise BadRequestError("You cannot change your own role or disable your own account")

        if "full_name" in changes and changes["full_name"] is not None:
            user.full_name = changes["full_name"]

        was_manager = user.role == RoleEnum.manager
        user.role = new_role
        if new_role != RoleEnum.employee:
            user.manager_id = None
        elif "manager_id" in changes:
            user.manager_id = self._validated_manager_id(changes["manager_id"])

        if changes.get("is_active") is not None:
            user.is_active = changes["is_active"]
            if not user.is_active and user.manager_id is not None:
                user.manager_id = None

        # A manager who is demoted or disabled leaves their team unassigned
        # rather than stranded with nobody able to approve their expenses.
        if was_manager and (user.role != RoleEnum.manager or not user.is_active):
            self.repo.unassign_reports(user.id)

        return self.repo.save(user)

    def update_role(self, admin: User, user_id: int, role: RoleEnum) -> User:
        if user_id == admin.id:
            raise BadRequestError("Admins cannot change their own role")
        return self.update_user(admin, user_id, {"role": role})

    def reset_password(self, user_id: int, password: str) -> User:
        """Admin sets a temporary password (the practical 'forgot password' path)."""
        user = self._get_or_404(user_id)
        user.hashed_password = hash_password(password)
        user.must_change_password = True
        return self.repo.save(user)

    def ensure_first_admin(self, email: str, password: str) -> Optional[User]:
        """Create the very first admin if the system has none. Safe to call every startup."""
        if self.repo.has_admin():
            return None
        if len(password) < 8:
            raise RuntimeError("FIRST_ADMIN_PASSWORD must be at least 8 characters")
        existing = self.repo.get_by_email(email)
        if existing:
            existing.role = RoleEnum.admin
            existing.is_active = True
            existing.manager_id = None
            return self.repo.save(existing)
        return self.repo.create(
            email=email,
            hashed_password=hash_password(password),
            full_name="Administrator",
            role=RoleEnum.admin,
            must_change_password=True,
        )

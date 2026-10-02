from sqlalchemy.orm import Session

from app.exceptions import BadRequestError, NotFoundError
from app.models.user import RoleEnum, User
from app.repositories.user_repository import UserRepository


class AdminService:
    def __init__(self, db: Session):
        self.repo = UserRepository(db)

    def list_users(self) -> list[User]:
        return self.repo.list_all()

    def update_role(self, admin: User, user_id: int, role: RoleEnum) -> User:
        if user_id == admin.id:
            raise BadRequestError("Admins cannot change their own role")

        user = self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")

        return self.repo.update_role(user, role)

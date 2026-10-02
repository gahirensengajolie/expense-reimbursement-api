from typing import Optional

from sqlalchemy.orm import Session

from app.models.user import RoleEnum, User


class UserRepository:
    """
    Owns all direct SQLAlchemy queries for User. No business rules live
    here -- just "how do I get/save this data". Business rules (can this
    user do X) belong in the service layer.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def list_all(self) -> list[User]:
        return self.db.query(User).all()

    def create(self, email: str, hashed_password: str, full_name: str) -> User:
        user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            role=RoleEnum.employee,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_role(self, user: User, role: RoleEnum) -> User:
        user.role = role
        self.db.commit()
        self.db.refresh(user)
        return user

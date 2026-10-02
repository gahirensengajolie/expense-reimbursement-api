from sqlalchemy.orm import Session

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.exceptions import AuthenticationError, BadRequestError, ForbiddenError
from app.models.user import User
from app.repositories.user_repository import UserRepository


class AuthService:
    def __init__(self, db: Session):
        self.repo = UserRepository(db)

    def register(self, email: str, password: str, full_name: str) -> User:
        if self.repo.get_by_email(email):
            raise BadRequestError("Email already registered")
        return self.repo.create(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
        )

    def authenticate(self, email: str, password: str) -> User:
        user = self.repo.get_by_email(email)
        # Same generic error whether the email exists or the password is
        # wrong -- prevents user enumeration via distinct error messages.
        if not user or not verify_password(password, user.hashed_password):
            raise AuthenticationError("Invalid email or password")
        if not user.is_active:
            raise ForbiddenError("Account is disabled")
        return user

    def issue_tokens(self, user: User) -> tuple[str, str]:
        access = create_access_token(subject=str(user.id), role=user.role.value)
        refresh = create_refresh_token(subject=str(user.id))
        return access, refresh

    def refresh_tokens(self, refresh_token: str) -> tuple[str, str]:
        data = decode_token(refresh_token)
        if not data or data.get("type") != "refresh":
            raise AuthenticationError("Invalid refresh token")

        user = self.repo.get_by_id(int(data["sub"]))
        if not user or not user.is_active:
            raise AuthenticationError("Invalid refresh token")

        return self.issue_tokens(user)

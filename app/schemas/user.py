from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.models.user import RoleEnum


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=100)


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: RoleEnum
    is_active: bool
    manager_id: Optional[int] = None
    must_change_password: bool = False

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class RoleUpdateRequest(BaseModel):
    role: RoleEnum


class AdminUserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=100)
    role: RoleEnum = RoleEnum.employee
    password: str = Field(min_length=8, max_length=128)
    manager_id: Optional[int] = None


class UserUpdate(BaseModel):
    """Partial update: only fields the client actually sends are applied."""

    full_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    role: Optional[RoleEnum] = None
    manager_id: Optional[int] = None
    is_active: Optional[bool] = None


class PasswordResetRequest(BaseModel):
    password: str = Field(min_length=8, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class AuthConfig(BaseModel):
    allow_self_registration: bool

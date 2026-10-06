import enum

from sqlalchemy import Boolean, Column, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class RoleEnum(str, enum.Enum):
    employee = "employee"
    manager = "manager"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(Enum(RoleEnum), default=RoleEnum.employee, nullable=False)
    is_active = Column(Boolean, default=True)

    # Team structure: an employee may be assigned to one manager.
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    # True for admin-created / reset accounts until the person picks their own password.
    must_change_password = Column(Boolean, default=False, nullable=False)

    manager = relationship("User", remote_side=[id], foreign_keys=[manager_id])

    expenses = relationship("Expense", back_populates="owner", foreign_keys="Expense.owner_id")

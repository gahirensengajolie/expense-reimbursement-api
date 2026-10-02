"""
Unit tests for ExpenseService, exercised directly -- no FastAPI app, no
TestClient, no HTTP layer at all. This is the actual payoff of the
service/repository split: business logic can be verified in isolation,
which is faster to run and pins down exactly where a bug lives (service
vs. router vs. framework wiring) when a test fails.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.core.security import hash_password
from app.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.user import RoleEnum, User
from app.services.expense_service import ExpenseService

engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestingSession = sessionmaker(bind=engine)


@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSession()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def make_user(db, email, role=RoleEnum.employee):
    user = User(email=email, hashed_password=hash_password("x"), full_name="U", role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_service_create_starts_as_draft(db):
    user = make_user(db, "svc1@example.com")
    service = ExpenseService(db)

    expense = service.create(user, "travel", 25.0, "taxi")
    assert expense.status.value == "draft"
    assert expense.owner_id == user.id


def test_service_blocks_editing_after_submit(db):
    user = make_user(db, "svc2@example.com")
    service = ExpenseService(db)

    expense = service.create(user, "travel", 25.0, "taxi")
    service.submit(expense.id, user)

    with pytest.raises(ConflictError):
        service.update(expense.id, user, {"amount": 99})


def test_service_blocks_self_review(db):
    manager = make_user(db, "svc3@example.com", role=RoleEnum.manager)
    service = ExpenseService(db)

    expense = service.create(manager, "travel", 25.0, "taxi")
    service.submit(expense.id, manager)

    with pytest.raises(ForbiddenError):
        service.review(expense.id, manager, approve=True, comment="self-approving")


def test_service_delete_only_allowed_on_draft(db):
    user = make_user(db, "svc4@example.com")
    service = ExpenseService(db)

    expense = service.create(user, "travel", 25.0, "taxi")
    service.submit(expense.id, user)

    with pytest.raises(ConflictError):
        service.delete(expense.id, user)


def test_service_delete_removes_draft(db):
    user = make_user(db, "svc5@example.com")
    service = ExpenseService(db)

    expense = service.create(user, "travel", 25.0, "taxi")
    service.delete(expense.id, user)

    with pytest.raises(NotFoundError):
        service.get(expense.id, user)


def test_service_employee_cannot_see_others_expense(db):
    alice = make_user(db, "svc6a@example.com")
    bob = make_user(db, "svc6b@example.com")
    service = ExpenseService(db)

    expense = service.create(alice, "travel", 25.0, "taxi")

    with pytest.raises(NotFoundError):
        service.get(expense.id, bob)

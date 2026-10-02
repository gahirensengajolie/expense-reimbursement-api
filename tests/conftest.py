import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.main import app

TEST_DB_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def register_and_login(
    client, email="user@example.com", password="StrongPass123", full_name="Test User"
):
    client.post(
        "/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )
    resp = client.post("/auth/login", json={"email": email, "password": password})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def make_admin(db_session, email):
    from app.models.user import RoleEnum, User

    user = db_session.query(User).filter(User.email == email).first()
    user.role = RoleEnum.admin
    db_session.commit()


def make_manager(db_session, email):
    from app.models.user import RoleEnum, User

    user = db_session.query(User).filter(User.email == email).first()
    user.role = RoleEnum.manager
    db_session.commit()

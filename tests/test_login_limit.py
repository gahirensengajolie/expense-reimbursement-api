from app.core.config import settings
from tests.conftest import register_and_login


def attempt(client, password):
    return client.post("/auth/login", json={"email": "limit@example.com", "password": password})


def test_login_attempts_are_limited_per_minute(client, monkeypatch):
    register_and_login(client, "limit@example.com")  # one successful sign-in already counted
    monkeypatch.setattr(settings, "login_max_attempts", 3)

    assert attempt(client, "wrong-password").status_code == 401  # 2nd attempt
    assert attempt(client, "wrong-password").status_code == 401  # 3rd attempt
    assert attempt(client, "wrong-password").status_code == 429  # over the limit


def test_default_limit_is_five():
    assert settings.login_max_attempts == 5

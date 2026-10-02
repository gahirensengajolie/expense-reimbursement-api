import pytest

from app.core.config import DEFAULT_SECRET_KEY, Settings, validate_production_settings

GOOD_KEY = "x" * 48


def test_development_allows_default_key():
    validate_production_settings(Settings(environment="development", secret_key=DEFAULT_SECRET_KEY))


@pytest.mark.parametrize(
    "key", [DEFAULT_SECRET_KEY, "change-this-to-a-long-random-string", "short"]
)
def test_production_rejects_weak_keys(key):
    with pytest.raises(RuntimeError):
        validate_production_settings(Settings(environment="production", secret_key=key))


def test_production_accepts_strong_key():
    validate_production_settings(Settings(environment="production", secret_key=GOOD_KEY))

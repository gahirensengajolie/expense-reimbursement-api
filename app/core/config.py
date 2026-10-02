from pydantic_settings import BaseSettings

DEFAULT_SECRET_KEY = "dev-only-change-me-in-env"


class Settings(BaseSettings):
    # SECURITY: never hardcode secrets. This default is only for local dev
    # and MUST be overridden via a .env file or real env vars in any
    # shared/staging/production environment.
    secret_key: str = DEFAULT_SECRET_KEY
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    database_url: str = "sqlite:///./expense.db"

    # Set ENVIRONMENT=production on the host. It turns on the startup
    # safety checks below.
    environment: str = "development"

    class Config:
        env_file = ".env"


def validate_production_settings(cfg: "Settings") -> None:
    """Refuse to start in production with a guessable JWT signing key.

    Anyone who knows the signing key can mint a valid admin token, so a
    default or short key on a public server is a full account takeover.
    """
    if cfg.environment.lower() != "production":
        return
    key = cfg.secret_key
    if key == DEFAULT_SECRET_KEY or key.startswith("change-this") or len(key) < 32:
        raise RuntimeError(
            "Unsafe SECRET_KEY for production: set SECRET_KEY to a random string of at "
            'least 32 characters (e.g. `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`).'
        )


settings = Settings()

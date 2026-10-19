"""Runtime configuration. The only module that reads environment variables."""

from functools import lru_cache
from typing import Literal, Self

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_SECRET = "dev-only-secret-change-me-in-production!!"  # noqa: S105 — rejected in production
_MIN_SECRET_LENGTH = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://taskmanager:taskmanager@localhost:5432/taskmanager"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: SecretStr = SecretStr(_DEV_SECRET)
    jwt_algorithm: str = "HS256"
    access_token_ttl_seconds: int = 15 * 60
    refresh_token_ttl_seconds: int = 7 * 24 * 60 * 60

    rate_limit_enabled: bool = True
    rate_limit_auth: str = "10/minute"
    rate_limit_api: str = "100/minute"
    rate_limit_storage_uri: str | None = None  # defaults to redis_url

    celery_broker_url: str | None = None  # defaults to redis_url
    celery_task_always_eager: bool = False
    event_publish_timeout_seconds: float = 2.0

    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    @property
    def broker_url(self) -> str:
        return self.celery_broker_url or self.redis_url

    @property
    def rate_limit_storage(self) -> str:
        return self.rate_limit_storage_uri or self.redis_url

    @model_validator(mode="after")
    def _require_strong_secret_in_production(self) -> Self:
        secret = self.jwt_secret.get_secret_value()
        if self.environment == "production" and (
            secret == _DEV_SECRET or len(secret) < _MIN_SECRET_LENGTH
        ):
            raise ValueError(f"JWT_SECRET must be set to at least {_MIN_SECRET_LENGTH} characters")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

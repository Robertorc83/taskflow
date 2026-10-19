"""The API's composition root: builds every adapter from Settings, once per application."""

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from taskmanager.application.ports import (
    Clock,
    EventPublisher,
    PasswordHasher,
    TokenService,
    UnitOfWork,
)
from taskmanager.infrastructure.clock import SystemClock
from taskmanager.infrastructure.config import Settings
from taskmanager.infrastructure.db.session import create_engine, create_session_factory
from taskmanager.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from taskmanager.infrastructure.rate_limit import RateLimiter
from taskmanager.infrastructure.security.passwords import Argon2PasswordHasher
from taskmanager.infrastructure.security.tokens import JwtTokenService
from taskmanager.infrastructure.tasks.celery_app import create_celery_app
from taskmanager.infrastructure.tasks.publisher import CeleryEventPublisher


@dataclass
class Container:
    settings: Settings
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    clock: Clock
    password_hasher: PasswordHasher
    token_service: TokenService
    event_publisher: EventPublisher
    rate_limiter: RateLimiter

    @classmethod
    def build(cls, settings: Settings) -> "Container":
        engine = create_engine(settings.database_url)
        clock = SystemClock()
        return cls(
            settings=settings,
            engine=engine,
            session_factory=create_session_factory(engine),
            clock=clock,
            password_hasher=Argon2PasswordHasher(),
            # Tokens always use real time: expiry is checked against the wall clock.
            token_service=JwtTokenService(
                secret=settings.jwt_secret.get_secret_value(),
                clock=SystemClock(),
                algorithm=settings.jwt_algorithm,
                access_ttl=timedelta(seconds=settings.access_token_ttl_seconds),
                refresh_ttl=timedelta(seconds=settings.refresh_token_ttl_seconds),
            ),
            event_publisher=CeleryEventPublisher(
                create_celery_app(settings), timeout_seconds=settings.event_publish_timeout_seconds
            ),
            rate_limiter=RateLimiter(
                settings.rate_limit_storage,
                auth_limit=settings.rate_limit_auth,
                api_limit=settings.rate_limit_api,
                enabled=settings.rate_limit_enabled,
            ),
        )

    def unit_of_work(self) -> UnitOfWork:
        return SqlAlchemyUnitOfWork(self.session_factory)

    async def check_database(self) -> None:
        async with self.engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

    async def aclose(self) -> None:
        await self.engine.dispose()

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool


def create_engine(database_url: str, *, pooled: bool = True) -> AsyncEngine:
    """`pooled=False` is for short-lived event loops (Celery jobs), where pooling can't help."""
    if pooled:
        return create_async_engine(database_url, pool_pre_ping=True)
    return create_async_engine(database_url, poolclass=NullPool)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)

from types import TracebackType
from typing import Self

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from taskmanager.application.exceptions import ConflictError
from taskmanager.infrastructure.db.repositories import (
    SqlAlchemyTaskRepository,
    SqlAlchemyUserRepository,
)


class SqlAlchemyUnitOfWork:
    """One session per use case. Anything not committed is rolled back on exit."""

    users: SqlAlchemyUserRepository
    tasks: SqlAlchemyTaskRepository

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> Self:
        self._session = self._session_factory()
        self.users = SqlAlchemyUserRepository(self._session)
        self.tasks = SqlAlchemyTaskRepository(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        session = self._active_session()
        await session.rollback()
        await session.close()
        self._session = None

    async def commit(self) -> None:
        try:
            await self._active_session().commit()
        except IntegrityError as error:
            # e.g. two concurrent registrations with the same email: the check in the use case
            # passed for both, the unique index catches the second.
            raise ConflictError("The change conflicts with existing data") from error

    def _active_session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("Unit of work used outside of `async with`")
        return self._session

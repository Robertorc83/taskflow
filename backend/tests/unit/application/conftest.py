from datetime import UTC, datetime

import pytest

from taskmanager.domain.entities import User
from tests.fakes import (
    FakeTokenService,
    FixedClock,
    InMemoryUnitOfWork,
    PlainTextPasswordHasher,
    RecordingNotifier,
    SpyEventPublisher,
)

NOW = datetime(2026, 10, 19, 9, 0, tzinfo=UTC)


@pytest.fixture
def uow() -> InMemoryUnitOfWork:
    return InMemoryUnitOfWork()


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock(NOW)


@pytest.fixture
def hasher() -> PlainTextPasswordHasher:
    return PlainTextPasswordHasher()


@pytest.fixture
def tokens() -> FakeTokenService:
    return FakeTokenService()


@pytest.fixture
def publisher() -> SpyEventPublisher:
    return SpyEventPublisher()


@pytest.fixture
def notifier() -> RecordingNotifier:
    return RecordingNotifier()


class UserFactory:
    def __init__(self, uow: InMemoryUnitOfWork) -> None:
        self._uow = uow

    async def __call__(
        self, email: str, *, password: str = "Password123!", active: bool = True
    ) -> User:
        user = User.register(
            email=email,
            full_name=email.split("@", maxsplit=1)[0].title(),
            hashed_password=PlainTextPasswordHasher().hash(password),
            now=NOW,
        )
        if not active:
            user.deactivate()
        await self._uow.users.add(user)
        return user


@pytest.fixture
def make_user(uow: InMemoryUnitOfWork) -> UserFactory:
    return UserFactory(uow)

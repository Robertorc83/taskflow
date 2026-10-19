"""Ports: what the application needs from the outside world, expressed as Protocols.

Infrastructure provides the adapters; tests provide fakes (tests/fakes.py).
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from types import TracebackType
from typing import Protocol, Self
from uuid import UUID

from taskmanager.application.dto import Page, PageRequest, TaskFilters, TokenPair, UserSummary
from taskmanager.domain.entities import Task, User
from taskmanager.domain.events import DomainEvent

# ------------------------------------------------------------------ persistence


class UserRepository(Protocol):
    async def add(self, user: User) -> None: ...
    async def save(self, user: User) -> None: ...
    async def get(self, user_id: UUID) -> User | None: ...
    async def get_by_email(self, email: str) -> User | None: ...
    async def get_many(self, user_ids: Iterable[UUID]) -> dict[UUID, User]: ...
    async def list(self, page: PageRequest) -> Page[User]: ...


class TaskRepository(Protocol):
    async def add(self, task: Task) -> None: ...
    async def save(self, task: Task) -> None: ...
    async def get(self, task_id: UUID, *, for_update: bool = False) -> Task | None:
        """`for_update` locks the row until the transaction ends (prevents lost updates)."""
        ...

    async def delete(self, task: Task) -> None: ...
    async def list_visible_to(
        self, user_id: UUID, filters: TaskFilters, page: PageRequest
    ) -> Page[Task]: ...


class UnitOfWork(Protocol):
    """A transaction. Changes are discarded unless `commit()` is called before exiting."""

    @property
    def users(self) -> UserRepository: ...
    @property
    def tasks(self) -> TaskRepository: ...

    async def __aenter__(self) -> Self: ...
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...
    async def commit(self) -> None: ...


# ------------------------------------------------------------------ services


class Clock(Protocol):
    def now(self) -> datetime: ...


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...
    def verify(self, password: str, hashed: str) -> bool: ...


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


class TokenService(Protocol):
    def issue(self, user_id: UUID) -> TokenPair: ...

    def verify(self, token: str, expected_type: TokenType) -> UUID:
        """Return the subject's user ID or raise AuthenticationError."""
        ...


class EventPublisher(Protocol):
    async def publish(self, event: DomainEvent) -> None: ...


@dataclass(frozen=True, slots=True)
class Notification:
    recipient: UserSummary
    subject: str
    body: str


class Notifier(Protocol):
    async def send(self, notification: Notification) -> None: ...


__all__ = [
    "Clock",
    "EventPublisher",
    "Notification",
    "Notifier",
    "PasswordHasher",
    "TaskRepository",
    "TokenService",
    "TokenType",
    "UnitOfWork",
    "UserRepository",
]

"""Hand-written test doubles for the application ports.

Fakes (working in-memory implementations) are preferred over mocks: they keep tests focused on
behavior instead of on which methods were called.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime, time
from types import TracebackType
from typing import Self
from uuid import UUID

from taskmanager.application.dto import (
    Page,
    PageRequest,
    TaskFilters,
    TaskOrdering,
    TaskScope,
    TokenPair,
)
from taskmanager.application.exceptions import AuthenticationError
from taskmanager.application.ports import Notification, TokenType
from taskmanager.domain.entities import Task, User
from taskmanager.domain.events import DomainEvent


class FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now

    def set_today(self, day: date) -> None:
        self._now = datetime.combine(day, time(9, 0), tzinfo=UTC)

    def advance_to(self, moment: datetime) -> None:
        self._now = moment


class PlainTextPasswordHasher:
    def hash(self, password: str) -> str:
        return f"plain:{password}"

    def verify(self, password: str, hashed: str) -> bool:
        return hashed == f"plain:{password}"


class FakeTokenService:
    """Readable, deterministic tokens: "<type>:<user id>"."""

    def issue(self, user_id: UUID) -> TokenPair:
        return TokenPair(
            access_token=f"access:{user_id}", refresh_token=f"refresh:{user_id}", expires_in=900
        )

    def verify(self, token: str, expected_type: TokenType) -> UUID:
        kind, _, subject = token.partition(":")
        if kind != expected_type.value:
            raise AuthenticationError("Invalid token")
        return UUID(subject)


@dataclass
class SpyEventPublisher:
    published: list[DomainEvent] = field(default_factory=list)

    async def publish(self, event: DomainEvent) -> None:
        self.published.append(event)


@dataclass
class RecordingNotifier:
    sent: list[Notification] = field(default_factory=list)

    async def send(self, notification: Notification) -> None:
        self.sent.append(notification)


class InMemoryUserRepository:
    def __init__(self) -> None:
        self.rows: dict[UUID, User] = {}

    async def add(self, user: User) -> None:
        self.rows[user.id] = replace(user)

    async def save(self, user: User) -> None:
        self.rows[user.id] = replace(user)

    async def get(self, user_id: UUID) -> User | None:
        user = self.rows.get(user_id)
        return replace(user) if user else None

    async def get_by_email(self, email: str) -> User | None:
        return next((replace(u) for u in self.rows.values() if u.email == email.lower()), None)

    async def get_many(self, user_ids: Iterable[UUID]) -> dict[UUID, User]:
        return {uid: replace(self.rows[uid]) for uid in set(user_ids) if uid in self.rows}

    async def list(self, page: PageRequest) -> Page[User]:
        users = sorted(self.rows.values(), key=lambda u: u.email)
        return Page(
            items=users[page.offset : page.offset + page.size],
            total=len(users),
            page=page.page,
            size=page.size,
        )


class InMemoryTaskRepository:
    def __init__(self) -> None:
        self.rows: dict[UUID, Task] = {}

    async def add(self, task: Task) -> None:
        self.rows[task.id] = replace(task)

    async def save(self, task: Task) -> None:
        self.rows[task.id] = replace(task)

    async def get(self, task_id: UUID) -> Task | None:
        task = self.rows.get(task_id)
        return replace(task) if task else None

    async def delete(self, task: Task) -> None:
        self.rows.pop(task.id, None)

    async def list_visible_to(
        self, user_id: UUID, filters: TaskFilters, page: PageRequest
    ) -> Page[Task]:
        def matches(task: Task) -> bool:
            in_scope = {
                TaskScope.ALL: user_id in (task.owner_id, task.assignee_id),
                TaskScope.OWNED: task.owner_id == user_id,
                TaskScope.ASSIGNED: task.assignee_id == user_id,
            }[filters.scope]
            if not in_scope or (filters.status and task.status != filters.status):
                return False
            if filters.due_from or filters.due_to:
                if task.due_date is None:
                    return False
                if filters.due_from and task.due_date < filters.due_from:
                    return False
                if filters.due_to and task.due_date > filters.due_to:
                    return False
            return True

        tasks = [t for t in self.rows.values() if matches(t)]
        if filters.ordering in (TaskOrdering.DUE_DATE, TaskOrdering.DUE_DATE_DESC):
            descending = filters.ordering is TaskOrdering.DUE_DATE_DESC
            dated = sorted(
                (t for t in tasks if t.due_date),
                key=lambda t: t.due_date or date.min,
                reverse=descending,
            )
            tasks = dated + [t for t in tasks if t.due_date is None]
        else:
            tasks.sort(
                key=lambda t: t.created_at, reverse=filters.ordering is TaskOrdering.CREATED_AT_DESC
            )
        return Page(
            items=[replace(t) for t in tasks[page.offset : page.offset + page.size]],
            total=len(tasks),
            page=page.page,
            size=page.size,
        )


class InMemoryUnitOfWork:
    def __init__(self) -> None:
        self.users = InMemoryUserRepository()
        self.tasks = InMemoryTaskRepository()
        self.commits = 0

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1

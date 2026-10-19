"""Data crossing the application boundary: commands in, read models out."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum, StrEnum
from math import ceil
from typing import ClassVar, Final, Literal
from uuid import UUID

from taskmanager.application.exceptions import InvalidInputError
from taskmanager.domain.entities import Task, User
from taskmanager.domain.value_objects import TaskStatus


class _Unset(Enum):
    UNSET = "UNSET"


UNSET: Final = _Unset.UNSET
type Unset = Literal[_Unset.UNSET]
"""Marks a field that was not provided, as opposed to one explicitly set to None."""


# ------------------------------------------------------------------ pagination


@dataclass(frozen=True, slots=True)
class PageRequest:
    page: int = 1
    size: int = 20

    MAX_SIZE: ClassVar[int] = 100

    def __post_init__(self) -> None:
        if self.page < 1:
            raise InvalidInputError("Page must be 1 or greater", field="page")
        if not 1 <= self.size <= self.MAX_SIZE:
            raise InvalidInputError(f"Size must be between 1 and {self.MAX_SIZE}", field="size")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


@dataclass(frozen=True, slots=True)
class Page[T]:
    items: Sequence[T]
    total: int
    page: int
    size: int

    @property
    def pages(self) -> int:
        return ceil(self.total / self.size)

    def map[R](self, transform: Callable[[T], R]) -> "Page[R]":
        return Page(
            items=[transform(item) for item in self.items],
            total=self.total,
            page=self.page,
            size=self.size,
        )


# ------------------------------------------------------------------ task queries


class TaskScope(StrEnum):
    ALL = "all"
    OWNED = "owned"
    ASSIGNED = "assigned"


class TaskOrdering(StrEnum):
    CREATED_AT = "created_at"
    CREATED_AT_DESC = "-created_at"
    DUE_DATE = "due_date"
    DUE_DATE_DESC = "-due_date"


@dataclass(frozen=True, slots=True)
class TaskFilters:
    scope: TaskScope = TaskScope.ALL
    status: TaskStatus | None = None
    due_from: date | None = None
    due_to: date | None = None
    ordering: TaskOrdering = TaskOrdering.CREATED_AT_DESC

    def __post_init__(self) -> None:
        if self.due_from and self.due_to and self.due_from > self.due_to:
            raise InvalidInputError("due_from must not be after due_to", field="due_from")


# ------------------------------------------------------------------ commands


@dataclass(frozen=True, slots=True)
class RegisterUserCommand:
    email: str
    full_name: str
    password: str


@dataclass(frozen=True, slots=True)
class CreateTaskCommand:
    title: str
    description: str | None = None
    due_date: date | None = None
    assignee_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class UpdateTaskCommand:
    title: str | Unset = UNSET
    description: str | Unset | None = UNSET
    due_date: date | Unset | None = UNSET
    status: TaskStatus | Unset = UNSET


# ------------------------------------------------------------------ read models


@dataclass(frozen=True, slots=True)
class UserSummary:
    id: UUID
    email: str
    full_name: str

    @classmethod
    def from_entity(cls, user: User) -> "UserSummary":
        return cls(id=user.id, email=user.email, full_name=user.full_name)


@dataclass(frozen=True, slots=True)
class UserDTO:
    id: UUID
    email: str
    full_name: str
    is_active: bool
    created_at: datetime

    @classmethod
    def from_entity(cls, user: User) -> "UserDTO":
        return cls(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            created_at=user.created_at,
        )


@dataclass(frozen=True, slots=True)
class TaskDTO:
    id: UUID
    title: str
    description: str | None
    status: TaskStatus
    due_date: date | None
    is_overdue: bool
    owner: UserSummary
    assignee: UserSummary | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None

    @classmethod
    def from_entity(
        cls, task: Task, *, owner: UserSummary, assignee: UserSummary | None, today: date
    ) -> "TaskDTO":
        return cls(
            id=task.id,
            title=task.title,
            description=task.description,
            status=task.status,
            due_date=task.due_date,
            is_overdue=task.is_overdue(today=today),
            owner=owner,
            assignee=assignee,
            created_at=task.created_at,
            updated_at=task.updated_at,
            completed_at=task.completed_at,
        )


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int

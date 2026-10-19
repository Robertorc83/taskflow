from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Self
from uuid import UUID, uuid4

from taskmanager.domain.events import DomainEvent, TaskAssigned, TaskCompleted
from taskmanager.domain.exceptions import (
    DueDateInPastError,
    InvalidStatusTransitionError,
    InvalidTaskDescriptionError,
    InvalidTaskTitleError,
    TaskAlreadyCompletedError,
)
from taskmanager.domain.value_objects import TaskStatus

TITLE_MAX_LENGTH = 200
DESCRIPTION_MAX_LENGTH = 2000


@dataclass(kw_only=True)
class Task:
    """A unit of work owned by one user and optionally assigned to another.

    All state changes go through methods so the invariants (SPEC-002, SPEC-004) always hold.
    """

    id: UUID
    title: str
    description: str | None
    status: TaskStatus
    due_date: date | None
    owner_id: UUID
    assignee_id: UUID | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    _events: list[DomainEvent] = field(default_factory=list, init=False, repr=False, compare=False)

    @classmethod
    def create(
        cls,
        *,
        title: str,
        owner_id: UUID,
        now: datetime,
        description: str | None = None,
        due_date: date | None = None,
    ) -> Self:
        cls._ensure_not_past(due_date, now)
        return cls(
            id=uuid4(),
            title=cls._clean_title(title),
            description=cls._clean_description(description),
            status=TaskStatus.PENDING,
            due_date=due_date,
            owner_id=owner_id,
            assignee_id=None,
            created_at=now,
            updated_at=now,
        )

    # ------------------------------------------------------------------ queries

    def is_owned_by(self, user_id: UUID) -> bool:
        return self.owner_id == user_id

    def is_visible_to(self, user_id: UUID) -> bool:
        return user_id in (self.owner_id, self.assignee_id)

    def is_overdue(self, *, today: date) -> bool:
        return (
            self.due_date is not None
            and self.due_date < today
            and self.status is not TaskStatus.COMPLETED
        )

    # ------------------------------------------------------------------ commands

    def rename(self, title: str, *, now: datetime) -> None:
        self.title = self._clean_title(title)
        self._touch(now)

    def describe(self, description: str | None, *, now: datetime) -> None:
        self.description = self._clean_description(description)
        self._touch(now)

    def reschedule(self, due_date: date | None, *, now: datetime) -> None:
        self._ensure_not_past(due_date, now)
        self.due_date = due_date
        self._touch(now)

    def change_status(self, status: TaskStatus, *, now: datetime) -> None:
        """Move between open states. Leaving `completed` this way reopens the task."""
        if status is TaskStatus.COMPLETED:
            raise InvalidStatusTransitionError("Use the complete action to complete a task")
        self.status = status
        self.completed_at = None
        self._touch(now)

    def complete(self, *, completed_by: UUID, now: datetime) -> None:
        if self.status is TaskStatus.COMPLETED:
            raise TaskAlreadyCompletedError("Task is already completed")
        self.status = TaskStatus.COMPLETED
        self.completed_at = now
        self._touch(now)
        self._events.append(TaskCompleted(task_id=self.id, completed_by=completed_by))

    def assign_to(self, assignee_id: UUID | None, *, assigned_by: UUID, now: datetime) -> None:
        self.assignee_id = assignee_id
        self._touch(now)
        if assignee_id is not None:
            self._events.append(
                TaskAssigned(task_id=self.id, assignee_id=assignee_id, assigned_by=assigned_by)
            )

    def pull_events(self) -> list[DomainEvent]:
        events, self._events = self._events, []
        return events

    # ------------------------------------------------------------------ helpers

    def _touch(self, now: datetime) -> None:
        self.updated_at = now

    @staticmethod
    def _clean_title(title: str) -> str:
        cleaned = title.strip()
        if not 1 <= len(cleaned) <= TITLE_MAX_LENGTH:
            raise InvalidTaskTitleError(f"Title must be 1-{TITLE_MAX_LENGTH} characters")
        return cleaned

    @staticmethod
    def _clean_description(description: str | None) -> str | None:
        cleaned = (description or "").strip()
        if len(cleaned) > DESCRIPTION_MAX_LENGTH:
            raise InvalidTaskDescriptionError(
                f"Description must be at most {DESCRIPTION_MAX_LENGTH} characters"
            )
        return cleaned or None

    @staticmethod
    def _ensure_not_past(due_date: date | None, now: datetime) -> None:
        if due_date is not None and due_date < now.date():
            raise DueDateInPastError("Due date cannot be in the past")

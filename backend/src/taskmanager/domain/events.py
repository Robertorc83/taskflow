"""Domain events: facts that already happened. They carry IDs only, never entity snapshots."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class TaskAssigned:
    task_id: UUID
    assignee_id: UUID
    assigned_by: UUID


@dataclass(frozen=True, slots=True)
class TaskCompleted:
    task_id: UUID
    completed_by: UUID


type DomainEvent = TaskAssigned | TaskCompleted

"""Task use cases (SPEC-002, SPEC-003, SPEC-004).

Authorization lives here, not in the HTTP layer:
- a task that is not visible to the actor is reported as *not found* (no existence leak);
- a visible task the actor may not modify is reported as *permission denied*.
Domain events are published only after the transaction commits.
"""

from collections.abc import Sequence
from datetime import date
from uuid import UUID

from taskmanager.application.dto import (
    UNSET,
    CreateTaskCommand,
    Page,
    PageRequest,
    TaskDTO,
    TaskFilters,
    UpdateTaskCommand,
    UserSummary,
)
from taskmanager.application.exceptions import (
    InvalidInputError,
    NotFoundError,
    PermissionDeniedError,
)
from taskmanager.application.ports import Clock, EventPublisher, UnitOfWork
from taskmanager.domain.entities import Task


class _TaskUseCase:
    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    @property
    def _today(self) -> date:
        return self._clock.now().date()

    async def _visible_task(self, uow: UnitOfWork, task_id: UUID, actor_id: UUID) -> Task:
        task = await uow.tasks.get(task_id)
        if task is None or not task.is_visible_to(actor_id):
            raise NotFoundError("Task not found")
        return task

    @staticmethod
    def _ensure_owner(task: Task, actor_id: UUID, action: str) -> None:
        if not task.is_owned_by(actor_id):
            raise PermissionDeniedError(f"Only the owner can {action} this task")

    @staticmethod
    async def _ensure_assignable(uow: UnitOfWork, user_id: UUID) -> None:
        user = await uow.users.get(user_id)
        if user is None or not user.is_active:
            raise InvalidInputError("Assignee must be an active user", field="assignee_id")

    async def _to_dtos(self, uow: UnitOfWork, tasks: Sequence[Task]) -> list[TaskDTO]:
        user_ids = {t.owner_id for t in tasks} | {t.assignee_id for t in tasks if t.assignee_id}
        users = {
            user_id: UserSummary.from_entity(user)
            for user_id, user in (await uow.users.get_many(user_ids)).items()
        }
        return [
            TaskDTO.from_entity(
                task,
                owner=users[task.owner_id],
                assignee=users[task.assignee_id] if task.assignee_id else None,
                today=self._today,
            )
            for task in tasks
        ]

    async def _to_dto(self, uow: UnitOfWork, task: Task) -> TaskDTO:
        return (await self._to_dtos(uow, [task]))[0]


class _PublishingTaskUseCase(_TaskUseCase):
    def __init__(self, uow: UnitOfWork, clock: Clock, publisher: EventPublisher) -> None:
        super().__init__(uow, clock)
        self._publisher = publisher

    async def _publish_events_of(self, task: Task) -> None:
        for event in task.pull_events():
            await self._publisher.publish(event)


class CreateTask(_PublishingTaskUseCase):
    async def execute(self, actor_id: UUID, command: CreateTaskCommand) -> TaskDTO:
        now = self._clock.now()
        async with self._uow as uow:
            task = Task.create(
                title=command.title,
                description=command.description,
                due_date=command.due_date,
                owner_id=actor_id,
                now=now,
            )
            if command.assignee_id is not None:
                await self._ensure_assignable(uow, command.assignee_id)
                task.assign_to(command.assignee_id, assigned_by=actor_id, now=now)
            await uow.tasks.add(task)
            result = await self._to_dto(uow, task)
            await uow.commit()
        await self._publish_events_of(task)
        return result


class GetTask(_TaskUseCase):
    async def execute(self, actor_id: UUID, task_id: UUID) -> TaskDTO:
        async with self._uow as uow:
            task = await self._visible_task(uow, task_id, actor_id)
            return await self._to_dto(uow, task)


class ListTasks(_TaskUseCase):
    async def execute(
        self, actor_id: UUID, filters: TaskFilters, page: PageRequest
    ) -> Page[TaskDTO]:
        async with self._uow as uow:
            tasks = await uow.tasks.list_visible_to(actor_id, filters, page)
            items = await self._to_dtos(uow, tasks.items)
        return Page(items=items, total=tasks.total, page=tasks.page, size=tasks.size)


class UpdateTask(_TaskUseCase):
    async def execute(self, actor_id: UUID, task_id: UUID, command: UpdateTaskCommand) -> TaskDTO:
        now = self._clock.now()
        async with self._uow as uow:
            task = await self._visible_task(uow, task_id, actor_id)
            self._ensure_owner(task, actor_id, "edit")
            if command.title is not UNSET:
                task.rename(command.title, now=now)
            if command.description is not UNSET:
                task.describe(command.description, now=now)
            if command.due_date is not UNSET and command.due_date != task.due_date:
                task.reschedule(command.due_date, now=now)
            if command.status is not UNSET and command.status != task.status:
                task.change_status(command.status, now=now)
            await uow.tasks.save(task)
            result = await self._to_dto(uow, task)
            await uow.commit()
        return result


class DeleteTask(_TaskUseCase):
    async def execute(self, actor_id: UUID, task_id: UUID) -> None:
        async with self._uow as uow:
            task = await self._visible_task(uow, task_id, actor_id)
            self._ensure_owner(task, actor_id, "delete")
            await uow.tasks.delete(task)
            await uow.commit()


class AssignTask(_PublishingTaskUseCase):
    async def execute(self, actor_id: UUID, task_id: UUID, assignee_id: UUID | None) -> TaskDTO:
        async with self._uow as uow:
            task = await self._visible_task(uow, task_id, actor_id)
            self._ensure_owner(task, actor_id, "assign")
            if assignee_id is not None:
                await self._ensure_assignable(uow, assignee_id)
            task.assign_to(assignee_id, assigned_by=actor_id, now=self._clock.now())
            await uow.tasks.save(task)
            result = await self._to_dto(uow, task)
            await uow.commit()
        await self._publish_events_of(task)
        return result


class CompleteTask(_PublishingTaskUseCase):
    """Owner or assignee may complete (SPEC-004 R4) — visibility is exactly that set."""

    async def execute(self, actor_id: UUID, task_id: UUID) -> TaskDTO:
        async with self._uow as uow:
            task = await self._visible_task(uow, task_id, actor_id)
            task.complete(completed_by=actor_id, now=self._clock.now())
            await uow.tasks.save(task)
            result = await self._to_dto(uow, task)
            await uow.commit()
        await self._publish_events_of(task)
        return result

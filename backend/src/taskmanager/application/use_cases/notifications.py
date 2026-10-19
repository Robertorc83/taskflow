"""Notification use cases, run by the background worker (SPEC-005).

They receive IDs, reload fresh state, and quietly do nothing if the task or users are gone.
"""

from uuid import UUID

from taskmanager.application.dto import UserSummary
from taskmanager.application.ports import Notification, Notifier, UnitOfWork


class NotifyTaskAssigned:
    def __init__(self, uow: UnitOfWork, notifier: Notifier) -> None:
        self._uow = uow
        self._notifier = notifier

    async def execute(self, task_id: UUID, assignee_id: UUID, assigned_by: UUID) -> None:
        if assignee_id == assigned_by:
            return
        async with self._uow as uow:
            task = await uow.tasks.get(task_id)
            users = await uow.users.get_many({assignee_id, assigned_by})
        if task is None or task.assignee_id != assignee_id or assignee_id not in users:
            return
        actor = users.get(assigned_by)
        actor_name = actor.full_name if actor else "Someone"
        await self._notifier.send(
            Notification(
                recipient=UserSummary.from_entity(users[assignee_id]),
                subject=f"New task assigned: {task.title}",
                body=f'{actor_name} assigned you the task "{task.title}".',
            )
        )


class NotifyTaskCompleted:
    def __init__(self, uow: UnitOfWork, notifier: Notifier) -> None:
        self._uow = uow
        self._notifier = notifier

    async def execute(self, task_id: UUID, completed_by: UUID) -> None:
        async with self._uow as uow:
            task = await uow.tasks.get(task_id)
            if task is None:
                return
            involved = {task.owner_id, completed_by}
            if task.assignee_id:
                involved.add(task.assignee_id)
            users = await uow.users.get_many(involved)
        actor = users.get(completed_by)
        actor_name = actor.full_name if actor else "Someone"
        recipients = (involved - {completed_by}) & users.keys()
        for recipient_id in sorted(recipients):
            await self._notifier.send(
                Notification(
                    recipient=UserSummary.from_entity(users[recipient_id]),
                    subject=f"Task completed: {task.title}",
                    body=f'{actor_name} completed the task "{task.title}".',
                )
            )

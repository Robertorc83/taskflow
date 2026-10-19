from datetime import date, timedelta
from uuid import uuid4

import pytest

from taskmanager.application.dto import (
    CreateTaskCommand,
    PageRequest,
    TaskDTO,
    TaskFilters,
    TaskScope,
    UpdateTaskCommand,
)
from taskmanager.application.exceptions import (
    InvalidInputError,
    NotFoundError,
    PermissionDeniedError,
)
from taskmanager.application.use_cases.tasks import (
    AssignTask,
    CompleteTask,
    CreateTask,
    DeleteTask,
    GetTask,
    ListTasks,
    ReopenTask,
    UpdateTask,
)
from taskmanager.domain.entities import User
from taskmanager.domain.events import TaskAssigned, TaskCompleted
from taskmanager.domain.exceptions import (
    DueDateInPastError,
    TaskAlreadyCompletedError,
    TaskNotCompletedError,
)
from taskmanager.domain.value_objects import TaskStatus
from tests.fakes import FixedClock, InMemoryUnitOfWork, SpyEventPublisher
from tests.unit.application.conftest import UserFactory


class Scenario:
    """Builds use cases over shared fakes, so tests read as Given/When/Then."""

    def __init__(
        self, uow: InMemoryUnitOfWork, clock: FixedClock, publisher: SpyEventPublisher
    ) -> None:
        self.uow, self.clock, self.publisher = uow, clock, publisher

    async def create(self, owner: User, title: str = "Write report", **kw: object) -> TaskDTO:
        command = CreateTaskCommand(title=title, **kw)  # type: ignore[arg-type]
        return await CreateTask(self.uow, self.clock, self.publisher).execute(owner.id, command)

    async def assign(self, actor: User, task: TaskDTO, assignee: User | None) -> TaskDTO:
        return await AssignTask(self.uow, self.clock, self.publisher).execute(
            actor.id, task.id, assignee.id if assignee else None
        )

    async def complete(self, actor: User, task: TaskDTO) -> TaskDTO:
        return await CompleteTask(self.uow, self.clock, self.publisher).execute(actor.id, task.id)

    async def update(self, actor: User, task: TaskDTO, **changes: object) -> TaskDTO:
        command = UpdateTaskCommand(**changes)  # type: ignore[arg-type]
        return await UpdateTask(self.uow, self.clock).execute(actor.id, task.id, command)


@pytest.fixture
def given(uow: InMemoryUnitOfWork, clock: FixedClock, publisher: SpyEventPublisher) -> Scenario:
    return Scenario(uow, clock, publisher)


@pytest.fixture
async def alice(make_user: UserFactory) -> User:
    return await make_user("alice@example.com")


@pytest.fixture
async def bob(make_user: UserFactory) -> User:
    return await make_user("bob@example.com")


@pytest.fixture
async def mallory(make_user: UserFactory) -> User:
    return await make_user("mallory@example.com")


class TestCreateTask:
    async def test_creates_a_pending_task_owned_by_the_actor(
        self, given: Scenario, alice: User
    ) -> None:
        task = await given.create(alice, due_date=date(2026, 11, 1))

        assert task.status is TaskStatus.PENDING
        assert task.owner.email == "alice@example.com"
        assert task.assignee is None
        assert given.uow.commits == 1
        assert given.publisher.published == []

    async def test_assigning_on_creation_publishes_an_event_after_commit(
        self, given: Scenario, alice: User, bob: User
    ) -> None:
        task = await given.create(alice, assignee_id=bob.id)

        assert task.assignee is not None
        assert task.assignee.email == "bob@example.com"
        assert given.publisher.published == [
            TaskAssigned(task_id=task.id, assignee_id=bob.id, assigned_by=alice.id)
        ]

    async def test_cannot_assign_on_creation_to_an_unknown_user(
        self, given: Scenario, alice: User
    ) -> None:
        with pytest.raises(InvalidInputError):
            await given.create(alice, assignee_id=uuid4())
        assert given.uow.tasks.rows == {}


class TestReadingTasks:
    async def test_owner_and_assignee_can_get_the_task(
        self, given: Scenario, alice: User, bob: User
    ) -> None:
        task = await given.create(alice, assignee_id=bob.id)

        for reader in (alice, bob):
            fetched = await GetTask(given.uow, given.clock).execute(reader.id, task.id)
            assert fetched.id == task.id

    async def test_strangers_get_not_found(
        self, given: Scenario, alice: User, mallory: User
    ) -> None:
        task = await given.create(alice)

        with pytest.raises(NotFoundError):
            await GetTask(given.uow, given.clock).execute(mallory.id, task.id)

    async def test_overdue_is_computed_against_the_clock(
        self, given: Scenario, alice: User
    ) -> None:
        task = await given.create(alice, due_date=given.clock.now().date())
        given.clock.set_today(given.clock.now().date() + timedelta(days=1))

        fetched = await GetTask(given.uow, given.clock).execute(alice.id, task.id)

        assert fetched.is_overdue

    async def test_list_returns_visible_tasks_with_user_summaries(
        self, given: Scenario, alice: User, bob: User
    ) -> None:
        await given.create(alice, title="Mine")
        await given.create(bob, title="Assigned to me", assignee_id=alice.id)
        await given.create(bob, title="Not mine")

        page = await ListTasks(given.uow, given.clock).execute(
            alice.id, TaskFilters(), PageRequest()
        )

        assert sorted(t.title for t in page.items) == ["Assigned to me", "Mine"]
        assert page.total == 2

    async def test_list_by_scope(self, given: Scenario, alice: User, bob: User) -> None:
        await given.create(alice, title="Mine")
        await given.create(bob, title="Assigned to me", assignee_id=alice.id)

        page = await ListTasks(given.uow, given.clock).execute(
            alice.id, TaskFilters(scope=TaskScope.ASSIGNED), PageRequest()
        )

        assert [t.title for t in page.items] == ["Assigned to me"]


class TestUpdateTask:
    async def test_owner_updates_only_the_provided_fields(
        self, given: Scenario, alice: User
    ) -> None:
        task = await given.create(alice, description="keep me", due_date=date(2026, 11, 1))

        updated = await given.update(alice, task, title="New", status=TaskStatus.IN_PROGRESS)

        assert updated.title == "New"
        assert updated.status is TaskStatus.IN_PROGRESS
        assert updated.description == "keep me"
        assert updated.due_date == date(2026, 11, 1)

    async def test_explicit_none_clears_optional_fields(self, given: Scenario, alice: User) -> None:
        task = await given.create(alice, description="x", due_date=date(2026, 11, 1))

        updated = await given.update(alice, task, description=None, due_date=None)

        assert (updated.description, updated.due_date) == (None, None)

    async def test_an_overdue_task_can_be_edited_when_its_date_is_resent_unchanged(
        self, given: Scenario, alice: User
    ) -> None:
        task = await given.create(alice, due_date=date(2026, 10, 20))
        given.clock.set_today(date(2026, 12, 1))

        updated = await given.update(alice, task, title="Late", due_date=date(2026, 10, 20))

        assert updated.title == "Late"

    async def test_moving_the_due_date_into_the_past_is_rejected(
        self, given: Scenario, alice: User
    ) -> None:
        task = await given.create(alice)

        with pytest.raises(DueDateInPastError):
            await given.update(alice, task, due_date=date(2026, 1, 1))

    async def test_assignee_is_denied_and_stranger_gets_not_found(
        self, given: Scenario, alice: User, bob: User, mallory: User
    ) -> None:
        task = await given.create(alice, assignee_id=bob.id)

        with pytest.raises(PermissionDeniedError):
            await given.update(bob, task, title="Bob's")
        with pytest.raises(NotFoundError):
            await given.update(mallory, task, title="Mallory's")


class TestDeleteTask:
    async def test_owner_deletes(self, given: Scenario, alice: User) -> None:
        task = await given.create(alice)

        await DeleteTask(given.uow, given.clock).execute(alice.id, task.id)

        assert given.uow.tasks.rows == {}

    async def test_assignee_cannot_delete(self, given: Scenario, alice: User, bob: User) -> None:
        task = await given.create(alice, assignee_id=bob.id)

        with pytest.raises(PermissionDeniedError):
            await DeleteTask(given.uow, given.clock).execute(bob.id, task.id)


class TestAssignTask:
    async def test_owner_assigns_and_event_is_published(
        self, given: Scenario, alice: User, bob: User
    ) -> None:
        task = await given.create(alice)

        assigned = await given.assign(alice, task, bob)

        assert assigned.assignee is not None
        assert assigned.assignee.id == bob.id
        assert given.publisher.published == [
            TaskAssigned(task_id=task.id, assignee_id=bob.id, assigned_by=alice.id)
        ]

    async def test_unassign(self, given: Scenario, alice: User, bob: User) -> None:
        task = await given.create(alice, assignee_id=bob.id)

        assert (await given.assign(alice, task, None)).assignee is None

    async def test_inactive_users_cannot_be_assigned(
        self, given: Scenario, alice: User, make_user: UserFactory
    ) -> None:
        task = await given.create(alice)
        inactive = await make_user("gone@example.com", active=False)

        with pytest.raises(InvalidInputError):
            await given.assign(alice, task, inactive)

    async def test_only_the_owner_can_reassign(
        self, given: Scenario, alice: User, bob: User
    ) -> None:
        task = await given.create(alice, assignee_id=bob.id)

        with pytest.raises(PermissionDeniedError):
            await given.assign(bob, task, bob)


class TestCompleteTask:
    async def test_assignee_completes_and_event_is_published(
        self, given: Scenario, alice: User, bob: User
    ) -> None:
        task = await given.create(alice, assignee_id=bob.id)
        given.publisher.published.clear()

        completed = await given.complete(bob, task)

        assert completed.status is TaskStatus.COMPLETED
        assert completed.completed_at == given.clock.now()
        assert given.publisher.published == [TaskCompleted(task_id=task.id, completed_by=bob.id)]

    async def test_completing_twice_is_a_conflict_and_publishes_nothing_more(
        self, given: Scenario, alice: User
    ) -> None:
        task = await given.create(alice)
        await given.complete(alice, task)

        with pytest.raises(TaskAlreadyCompletedError):
            await given.complete(alice, task)
        assert len(given.publisher.published) == 1

    async def test_strangers_cannot_complete(
        self, given: Scenario, alice: User, mallory: User
    ) -> None:
        task = await given.create(alice)

        with pytest.raises(NotFoundError):
            await given.complete(mallory, task)

    async def test_reopening_through_update_clears_completion(
        self, given: Scenario, alice: User
    ) -> None:
        task = await given.create(alice)
        await given.complete(alice, task)

        reopened = await given.update(alice, task, status=TaskStatus.PENDING)

        assert reopened.status is TaskStatus.PENDING
        assert reopened.completed_at is None


class TestReopenTask:
    """CR-004: whoever may complete a task may undo that."""

    async def test_assignee_reopens_and_completion_is_cleared(
        self, given: Scenario, alice: User, bob: User
    ) -> None:
        task = await given.create(alice, assignee_id=bob.id)
        await given.complete(bob, task)

        reopened = await ReopenTask(given.uow, given.clock).execute(bob.id, task.id)

        assert reopened.status is TaskStatus.PENDING
        assert reopened.completed_at is None

    async def test_reopening_an_open_task_is_a_conflict(self, given: Scenario, alice: User) -> None:
        task = await given.create(alice)

        with pytest.raises(TaskNotCompletedError):
            await ReopenTask(given.uow, given.clock).execute(alice.id, task.id)

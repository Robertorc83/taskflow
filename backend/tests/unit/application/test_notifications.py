from uuid import uuid4

from taskmanager.application.use_cases.notifications import NotifyTaskAssigned, NotifyTaskCompleted
from taskmanager.domain.entities import Task, User
from tests.fakes import FixedClock, InMemoryUnitOfWork, RecordingNotifier
from tests.unit.application.conftest import UserFactory


async def _task(
    uow: InMemoryUnitOfWork, clock: FixedClock, owner: User, assignee: User | None = None
) -> Task:
    task = Task.create(title="Prepare demo", owner_id=owner.id, now=clock.now())
    if assignee:
        task.assign_to(assignee.id, assigned_by=owner.id, now=clock.now())
    await uow.tasks.add(task)
    return task


class TestNotifyTaskAssigned:
    async def test_notifies_the_assignee_with_title_and_actor(
        self,
        uow: InMemoryUnitOfWork,
        clock: FixedClock,
        notifier: RecordingNotifier,
        make_user: UserFactory,
    ) -> None:
        alice, bob = await make_user("alice@example.com"), await make_user("bob@example.com")
        task = await _task(uow, clock, alice, bob)

        await NotifyTaskAssigned(uow, notifier).execute(task.id, bob.id, alice.id)

        [sent] = notifier.sent
        assert sent.recipient.email == "bob@example.com"
        assert "Prepare demo" in sent.subject
        assert "Alice" in sent.body

    async def test_self_assignment_is_silent(
        self,
        uow: InMemoryUnitOfWork,
        clock: FixedClock,
        notifier: RecordingNotifier,
        make_user: UserFactory,
    ) -> None:
        alice = await make_user("alice@example.com")
        task = await _task(uow, clock, alice, alice)

        await NotifyTaskAssigned(uow, notifier).execute(task.id, alice.id, alice.id)

        assert notifier.sent == []

    async def test_is_a_no_op_when_the_task_is_gone_or_reassigned(
        self,
        uow: InMemoryUnitOfWork,
        clock: FixedClock,
        notifier: RecordingNotifier,
        make_user: UserFactory,
    ) -> None:
        alice, bob = await make_user("alice@example.com"), await make_user("bob@example.com")
        reassigned = await _task(uow, clock, alice, alice)

        await NotifyTaskAssigned(uow, notifier).execute(uuid4(), bob.id, alice.id)
        await NotifyTaskAssigned(uow, notifier).execute(reassigned.id, bob.id, alice.id)

        assert notifier.sent == []


class TestNotifyTaskCompleted:
    async def test_notifies_everyone_involved_except_the_actor(
        self,
        uow: InMemoryUnitOfWork,
        clock: FixedClock,
        notifier: RecordingNotifier,
        make_user: UserFactory,
    ) -> None:
        alice, bob = await make_user("alice@example.com"), await make_user("bob@example.com")
        task = await _task(uow, clock, alice, bob)

        await NotifyTaskCompleted(uow, notifier).execute(task.id, bob.id)

        assert [n.recipient.email for n in notifier.sent] == ["alice@example.com"]
        assert "completed" in notifier.sent[0].subject.lower()

    async def test_completing_your_own_unassigned_task_is_silent(
        self,
        uow: InMemoryUnitOfWork,
        clock: FixedClock,
        notifier: RecordingNotifier,
        make_user: UserFactory,
    ) -> None:
        alice = await make_user("alice@example.com")
        task = await _task(uow, clock, alice)

        await NotifyTaskCompleted(uow, notifier).execute(task.id, alice.id)

        assert notifier.sent == []

    async def test_is_a_no_op_when_the_task_is_gone(
        self, uow: InMemoryUnitOfWork, notifier: RecordingNotifier
    ) -> None:
        await NotifyTaskCompleted(uow, notifier).execute(uuid4(), uuid4())

        assert notifier.sent == []

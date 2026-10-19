from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest

from taskmanager.domain.entities import Task
from taskmanager.domain.events import TaskAssigned, TaskCompleted
from taskmanager.domain.exceptions import (
    DueDateInPastError,
    InvalidStatusTransitionError,
    InvalidTaskDescriptionError,
    InvalidTaskTitleError,
    TaskAlreadyCompletedError,
    TaskNotCompletedError,
)
from taskmanager.domain.value_objects import TaskStatus

NOW = datetime(2026, 10, 19, 9, 0, tzinfo=UTC)
TODAY = NOW.date()
LATER = NOW + timedelta(hours=1)
OWNER = uuid4()


def make_task(**overrides: object) -> Task:
    params: dict[str, object] = {"title": "Write report", "owner_id": OWNER, "now": NOW}
    params.update(overrides)
    return Task.create(**params)  # type: ignore[arg-type]


class TestCreatingATask:
    def test_a_new_task_is_pending_and_owned_by_its_creator(self) -> None:
        task = make_task()

        assert task.status is TaskStatus.PENDING
        assert task.owner_id == OWNER
        assert task.assignee_id is None
        assert task.created_at == task.updated_at == NOW
        assert task.completed_at is None

    def test_title_and_description_are_trimmed(self) -> None:
        task = make_task(title="  Write report  ", description="  details  ")

        assert task.title == "Write report"
        assert task.description == "details"

    def test_a_blank_description_is_stored_as_none(self) -> None:
        assert make_task(description="   ").description is None

    @pytest.mark.parametrize("title", ["", "   ", "x" * 201])
    def test_title_must_be_between_1_and_200_characters(self, title: str) -> None:
        with pytest.raises(InvalidTaskTitleError):
            make_task(title=title)

    def test_title_of_exactly_200_characters_is_accepted(self) -> None:
        assert len(make_task(title="x" * 200).title) == 200

    def test_description_is_limited_to_2000_characters(self) -> None:
        with pytest.raises(InvalidTaskDescriptionError):
            make_task(description="x" * 2001)

    def test_due_date_cannot_be_in_the_past(self) -> None:
        with pytest.raises(DueDateInPastError):
            make_task(due_date=TODAY - timedelta(days=1))

    def test_due_date_can_be_today(self) -> None:
        assert make_task(due_date=TODAY).due_date == TODAY

    def test_creating_a_task_emits_no_events(self) -> None:
        assert make_task().pull_events() == []


class TestUpdatingATask:
    def test_rename_updates_title_and_timestamp(self) -> None:
        task = make_task()

        task.rename("New title", now=LATER)

        assert task.title == "New title"
        assert task.updated_at == LATER

    def test_rename_validates_the_title(self) -> None:
        with pytest.raises(InvalidTaskTitleError):
            make_task().rename(" ", now=LATER)

    def test_description_can_be_cleared(self) -> None:
        task = make_task(description="details")

        task.describe(None, now=LATER)

        assert task.description is None

    def test_reschedule_rejects_past_dates(self) -> None:
        with pytest.raises(DueDateInPastError):
            make_task().reschedule(date(2026, 1, 1), now=LATER)

    def test_reschedule_can_clear_the_due_date(self) -> None:
        task = make_task(due_date=date(2026, 11, 1))

        task.reschedule(None, now=LATER)

        assert task.due_date is None

    def test_status_can_move_to_in_progress(self) -> None:
        task = make_task()

        task.change_status(TaskStatus.IN_PROGRESS, now=LATER)

        assert task.status is TaskStatus.IN_PROGRESS
        assert task.updated_at == LATER

    def test_status_cannot_be_set_to_completed_directly(self) -> None:
        with pytest.raises(InvalidStatusTransitionError):
            make_task().change_status(TaskStatus.COMPLETED, now=LATER)

    def test_changing_status_of_a_completed_task_reopens_it(self) -> None:
        task = make_task()
        task.complete(completed_by=OWNER, now=LATER)

        task.change_status(TaskStatus.PENDING, now=LATER)

        assert task.status is TaskStatus.PENDING
        assert task.completed_at is None


class TestCompletingATask:
    def test_complete_sets_status_and_completion_time_and_emits_event(self) -> None:
        task = make_task()

        task.complete(completed_by=OWNER, now=LATER)

        assert task.status is TaskStatus.COMPLETED
        assert task.completed_at == LATER
        assert task.pull_events() == [TaskCompleted(task_id=task.id, completed_by=OWNER)]

    def test_a_completed_task_cannot_be_completed_again(self) -> None:
        task = make_task()
        task.complete(completed_by=OWNER, now=LATER)

        with pytest.raises(TaskAlreadyCompletedError):
            task.complete(completed_by=OWNER, now=LATER)

    def test_pulling_events_empties_the_queue(self) -> None:
        task = make_task()
        task.complete(completed_by=OWNER, now=LATER)

        task.pull_events()

        assert task.pull_events() == []


class TestAssigningATask:
    def test_assign_sets_assignee_and_emits_event(self) -> None:
        task, assignee = make_task(), uuid4()

        task.assign_to(assignee, assigned_by=OWNER, now=LATER)

        assert task.assignee_id == assignee
        assert task.updated_at == LATER
        assert task.pull_events() == [
            TaskAssigned(task_id=task.id, assignee_id=assignee, assigned_by=OWNER)
        ]

    def test_unassign_clears_assignee_without_event(self) -> None:
        task = make_task()
        task.assign_to(uuid4(), assigned_by=OWNER, now=LATER)
        task.pull_events()

        task.assign_to(None, assigned_by=OWNER, now=LATER)

        assert task.assignee_id is None
        assert task.pull_events() == []


class TestAccessRules:
    def test_owner_and_assignee_can_see_the_task_but_strangers_cannot(self) -> None:
        task, assignee = make_task(), uuid4()
        task.assign_to(assignee, assigned_by=OWNER, now=LATER)

        assert task.is_visible_to(OWNER)
        assert task.is_visible_to(assignee)
        assert not task.is_visible_to(uuid4())

    def test_only_the_owner_owns_the_task(self) -> None:
        task, assignee = make_task(), uuid4()
        task.assign_to(assignee, assigned_by=OWNER, now=LATER)

        assert task.is_owned_by(OWNER)
        assert not task.is_owned_by(assignee)


class TestOverdue:
    def test_a_task_past_its_due_date_is_overdue(self) -> None:
        task = make_task(due_date=TODAY)

        assert not task.is_overdue(today=TODAY)
        assert task.is_overdue(today=TODAY + timedelta(days=1))

    def test_a_completed_task_is_never_overdue(self) -> None:
        task = make_task(due_date=TODAY)
        task.complete(completed_by=OWNER, now=LATER)

        assert not task.is_overdue(today=TODAY + timedelta(days=30))

    def test_a_task_without_due_date_is_never_overdue(self) -> None:
        assert not make_task().is_overdue(today=TODAY + timedelta(days=30))


class TestReopening:
    def test_reopen_clears_completion(self) -> None:
        task = make_task()
        task.complete(completed_by=OWNER, now=LATER)

        task.reopen(now=LATER)

        assert (task.status, task.completed_at) == (TaskStatus.PENDING, None)

    def test_only_completed_tasks_can_be_reopened(self) -> None:
        with pytest.raises(TaskNotCompletedError):
            make_task().reopen(now=LATER)


def test_only_owner_and_assignee_can_complete() -> None:
    task, assignee = make_task(), uuid4()
    task.assign_to(assignee, assigned_by=OWNER, now=LATER)

    assert task.can_be_completed_by(OWNER)
    assert task.can_be_completed_by(assignee)
    assert not task.can_be_completed_by(uuid4())

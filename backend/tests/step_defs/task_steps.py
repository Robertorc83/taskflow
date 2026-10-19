from typing import Any
from uuid import uuid4

from pytest_bdd import given, parsers, then, when

from tests.step_defs.world import World

Q = r'"(?P<{}>[^"]*)"'  # a quoted step argument


def _create_task(world: World, as_user: str | None = None, **payload: Any) -> dict[str, Any]:
    response = world.request("POST", "/tasks", as_user=as_user, json=payload)
    assert response.status_code == 201, response.text
    task: dict[str, Any] = response.json()
    return task


def _task_path(world: World, suffix: str = "") -> str:
    assert world.task_id is not None, "No task in this scenario"
    return f"/tasks/{world.task_id}{suffix}"


# ------------------------------------------------------------------------------ Given


@given(parsers.re(f"I have a task titled {Q.format('title')}"))
def have_task(world: World, title: str) -> None:
    world.task_id = _create_task(world, title=title)["id"]


@given(parsers.re(f"I have a task titled {Q.format('title')} due on {Q.format('due')}"))
def have_task_due(world: World, title: str, due: str) -> None:
    world.task_id = _create_task(world, title=title, due_date=due)["id"]


@given("I have the following tasks:")
def have_tasks(world: World, datatable: list[list[str]]) -> None:
    header, *rows = datatable
    for row in rows:
        spec = dict(zip(header, row, strict=True))
        task = _create_task(world, title=spec["title"], due_date=spec["due_date"] or None)
        if spec["status"] == "completed":
            world.request("POST", f"/tasks/{task['id']}/complete")
        elif spec["status"] != "pending":
            world.request("PATCH", f"/tasks/{task['id']}", json={"status": spec["status"]})
        assert world.response.status_code in {200, 201}, world.response.text


@given(parsers.re(f"{Q.format('email')} has a task titled {Q.format('title')} assigned to me"))
def other_user_task_assigned_to_me(world: World, email: str, title: str) -> None:
    assert world.current_email is not None
    me = world.user_ids[world.current_email]
    current = world.current_email
    world.log_in(email)
    _create_task(world, title=title, assignee_id=me)
    world.log_in(current)


@given(parsers.re(f"{Q.format('email')} has a task titled {Q.format('title')}"))
def other_user_task(world: World, email: str, title: str) -> None:
    current = world.current_email
    world.log_in(email)
    _create_task(world, title=title)
    if current is not None:
        world.log_in(current)


@given(parsers.re(f"the task is assigned to {Q.format('email')}"))
def task_is_assigned(world: World, email: str) -> None:
    assignee_id = world.ensure_user(email)
    response = world.request(
        "PUT", _task_path(world, "/assignee"), json={"assignee_id": assignee_id}
    )
    assert response.status_code == 200, response.text


@given("the task is completed")
def task_is_completed(world: World) -> None:
    response = world.request("POST", _task_path(world, "/complete"))
    assert response.status_code == 200, response.text


# ------------------------------------------------------------------------------ When


@when(parsers.re(f"I create a task titled {Q.format('title')}"))
def create_task(world: World, title: str) -> None:
    world.request("POST", "/tasks", json={"title": title})
    if world.response.status_code == 201:
        world.task_id = world.body["id"]


@when(parsers.re(f"I create a task titled {Q.format('title')} due on {Q.format('due')}"))
def create_task_due(world: World, title: str, due: str) -> None:
    world.request("POST", "/tasks", json={"title": title, "due_date": due})


@when(parsers.re(f"I create a task titled {Q.format('title')} assigned to {Q.format('email')}"))
def create_task_assigned(world: World, title: str, email: str) -> None:
    world.request("POST", "/tasks", json={"title": title, "assignee_id": world.user_ids[email]})


@when(parsers.parse("I create a task with a title of {length:d} characters"))
def create_task_long_title(world: World, length: int) -> None:
    world.request("POST", "/tasks", json={"title": "x" * length})


@when("I create a task with a whitespace-only title")
def create_task_blank_title(world: World) -> None:
    world.request("POST", "/tasks", json={"title": "   "})


@when("I view the task")
def view_task(world: World) -> None:
    world.request("GET", _task_path(world))


@when("I view a task that does not exist")
def view_missing_task(world: World) -> None:
    world.request("GET", f"/tasks/{uuid4()}")


@when(
    parsers.re(f"I update the task with title {Q.format('title')} and status {Q.format('status')}")
)
def update_title_and_status(world: World, title: str, status: str) -> None:
    world.request("PATCH", _task_path(world), json={"title": title, "status": status})


@when(parsers.re(f"I update the task with title {Q.format('title')}"))
def update_title(world: World, title: str) -> None:
    world.request("PATCH", _task_path(world), json={"title": title})


@when(parsers.re(f"I update the task with status {Q.format('status')}"))
def update_status(world: World, status: str) -> None:
    world.request("PATCH", _task_path(world), json={"status": status})


@when(parsers.re(f"I change the task's due date to {Q.format('due')}"))
def change_due_date(world: World, due: str) -> None:
    world.request("PATCH", _task_path(world), json={"due_date": due})


@when("I clear the task's due date")
def clear_due_date(world: World) -> None:
    world.request("PATCH", _task_path(world), json={"due_date": None})


@when("I delete the task")
def delete_task(world: World) -> None:
    world.request("DELETE", _task_path(world))


@when(parsers.re(f"I assign the task to {Q.format('email')}"))
def assign_task(world: World, email: str) -> None:
    assignee_id = world.ensure_user(email)
    world.request("PUT", _task_path(world, "/assignee"), json={"assignee_id": assignee_id})


@when("I assign the task to an unknown user")
def assign_task_to_unknown(world: World) -> None:
    world.request("PUT", _task_path(world, "/assignee"), json={"assignee_id": str(uuid4())})


@when("I unassign the task")
def unassign_task(world: World) -> None:
    world.request("PUT", _task_path(world, "/assignee"), json={"assignee_id": None})


@when("I complete the task")
def complete_task(world: World) -> None:
    world.request("POST", _task_path(world, "/complete"))


# ------------------------------------------------------------------------------ Then


@then(parsers.re(f"the task should have status {Q.format('status')}"))
def task_has_status(world: World, status: str) -> None:
    assert world.body["status"] == status


@then("I should be the owner of the task")
def i_own_the_task(world: World) -> None:
    assert world.current_email is not None
    assert world.body["owner"]["email"] == world.current_email


@then("the task should not be overdue")
def task_not_overdue(world: World) -> None:
    assert world.body["is_overdue"] is False


@then("the task should have no due date")
def task_has_no_due_date(world: World) -> None:
    assert world.body["due_date"] is None


@then(parsers.re(f"the task should be due on {Q.format('due')}"))
def task_due_on(world: World, due: str) -> None:
    assert world.body["due_date"] == due


@then(parsers.re(f"the task title should be {Q.format('title')}"))
def task_title_is(world: World, title: str) -> None:
    assert world.body["title"] == title


@then("the task should no longer exist")
def task_is_gone(world: World) -> None:
    assert world.request("GET", _task_path(world)).status_code == 404


@then(parsers.re(f"the task should be assigned to {Q.format('email')}"))
def task_assigned_to(world: World, email: str) -> None:
    assert world.body["assignee"]["email"] == email


@then("the task should have no assignee")
def task_has_no_assignee(world: World) -> None:
    assert world.body["assignee"] is None


@then("the task should have a completion time")
def task_has_completion_time(world: World) -> None:
    assert world.body["completed_at"] is not None


@then("the task should have no completion time")
def task_has_no_completion_time(world: World) -> None:
    assert world.body["completed_at"] is None


@then(parsers.re(f"a {Q.format('event')} event should be published for {Q.format('email')}"))
def event_published_for(world: World, event: str, email: str) -> None:
    recipients = {
        str(getattr(e, "assignee_id", None))
        for e in world.events.published
        if type(e).__name__ == event
    }
    assert world.user_ids[email] in recipients, world.events.published


@then(parsers.re(f"a {Q.format('event')} event should be published"))
def event_published(world: World, event: str) -> None:
    assert event in {type(e).__name__ for e in world.events.published}, world.events.published

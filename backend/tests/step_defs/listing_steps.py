from typing import Any

from pytest_bdd import parsers, then, when

from tests.step_defs.world import World

Q = r'"(?P<{}>[^"]*)"'


def _list(world: World, **params: Any) -> None:
    world.request("GET", "/tasks", params={"size": 100, **params})


@when("I list my tasks")
def list_tasks(world: World) -> None:
    _list(world)


@when(parsers.re(f"I list my tasks with status {Q.format('status')}"))
def list_by_status(world: World, status: str) -> None:
    _list(world, status=status)


@when(parsers.re(f"I list my tasks due between {Q.format('start')} and {Q.format('end')}"))
def list_due_between(world: World, start: str, end: str) -> None:
    _list(world, due_from=start, due_to=end)


@when(parsers.re(f"I list my tasks due from {Q.format('start')}"))
def list_due_from(world: World, start: str) -> None:
    _list(world, due_from=start)


@when(parsers.re(f"I list my tasks with status {Q.format('status')} due until {Q.format('end')}"))
def list_by_status_due_until(world: World, status: str, end: str) -> None:
    _list(world, status=status, due_to=end)


@when(parsers.re(f"I list my tasks ordered by {Q.format('ordering')}"))
def list_ordered(world: World, ordering: str) -> None:
    _list(world, ordering=ordering)


@when(parsers.parse("I list my tasks with page {page:d} and size {size:d}"))
def list_page(world: World, page: int, size: int) -> None:
    world.request("GET", "/tasks", params={"page": page, "size": size})


@when(parsers.re(f"I list tasks with scope {Q.format('scope')}"))
def list_scope(world: World, scope: str) -> None:
    _list(world, scope=scope)


@then(parsers.parse("I should see {count:d} tasks"))
def see_count(world: World, count: int) -> None:
    assert world.response.status_code == 200, world.response.text
    assert len(world.body["items"]) == count, [t["title"] for t in world.body["items"]]


@then(parsers.parse("the total should be {total:d}"))
def total_is(world: World, total: int) -> None:
    assert world.body["total"] == total


@then(parsers.parse("there should be {pages:d} pages"))
def pages_are(world: World, pages: int) -> None:
    assert world.body["pages"] == pages


@then(parsers.re(f"every task should have status {Q.format('status')}"))
def every_task_has_status(world: World, status: str) -> None:
    assert {task["status"] for task in world.body["items"]} == {status}


@then(parsers.re(f"I should see only {Q.format('title')}"))
def see_only(world: World, title: str) -> None:
    assert world.response.status_code == 200, world.response.text
    assert [task["title"] for task in world.body["items"]] == [title]


@then(parsers.re(f"the task titles should be in order {Q.format('titles')}"))
def titles_in_order(world: World, titles: str) -> None:
    expected = [title.strip() for title in titles.split(",")]
    assert [task["title"] for task in world.body["items"]] == expected

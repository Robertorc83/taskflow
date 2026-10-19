from pytest_bdd import given, parsers, then, when

from taskmanager.infrastructure.rate_limit import RateLimiter
from tests.step_defs.patterns import QUOTED as Q
from tests.step_defs.world import World

GENEROUS = "1000/minute"


@given(parsers.parse("the auth rate limit is {limit:d} requests per minute"))
def auth_rate_limit(world: World, limit: int) -> None:
    world.container.rate_limiter = RateLimiter(
        "memory://", auth_limit=f"{limit}/minute", api_limit=GENEROUS
    )


@given(parsers.parse("the API rate limit is {limit:d} requests per minute"))
def api_rate_limit(world: World, limit: int) -> None:
    world.container.rate_limiter = RateLimiter(
        "memory://", auth_limit=GENEROUS, api_limit=f"{limit}/minute"
    )


@when(
    parsers.re(
        f"I attempt to log in as {Q.format('email')} with password {Q.format('password')}"
        r" (?P<times>\d+) times"
    )
)
def attempt_logins(world: World, email: str, password: str, times: str) -> None:
    for _ in range(int(times)):
        world.request(
            "POST", "/auth/login", anonymous=True, json={"email": email, "password": password}
        )


@when(parsers.parse("I list my tasks {times:d} times"))
@given(parsers.parse("I have listed my tasks {times:d} times"))
def list_repeatedly(world: World, times: int) -> None:
    for _ in range(times):
        world.request("GET", "/tasks")


@when(parsers.re(f"{Q.format('email')} lists their tasks"))
def other_user_lists(world: World, email: str) -> None:
    world.request("GET", "/tasks", as_user=email)


@then(parsers.parse("the last response status should be {status:d}"))
def last_status(world: World, status: int) -> None:
    assert world.response.status_code == status, world.response.text


@then(parsers.parse("every response status should be {status:d}"))
def every_status(world: World, status: int) -> None:
    assert {r.status_code for r in world.responses} == {status}


@then("the response should tell me when to retry")
def tells_retry_after(world: World) -> None:
    assert int(world.response.headers["Retry-After"]) >= 1
    assert world.body["status"] == 429

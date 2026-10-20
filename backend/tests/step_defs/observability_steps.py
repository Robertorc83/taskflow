import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, then, when

from taskmanager.infrastructure.config import Settings
from taskmanager.presentation.app import create_app
from tests.step_defs.patterns import QUOTED as Q
from tests.step_defs.world import World

REQUEST_ID = "X-Request-ID"


@when(parsers.re(f"I request my profile with request ID {Q.format('request_id')}"))
def request_profile_with_id(world: World, request_id: str) -> None:
    world.request("GET", "/users/me", headers={REQUEST_ID: request_id})


@when(
    parsers.re(
        f"a browser on {Q.format('origin')} preflights a request with header {Q.format('header')}"
    )
)
def preflight(world: World, origin: str, header: str) -> None:
    world.responses.append(
        world.client.options(
            "/api/v1/tasks",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": header,
            },
        )
    )


@then("the response should have a request ID")
def has_request_id(world: World) -> None:
    assert world.response.headers.get(REQUEST_ID)


@then(parsers.re(f"the response request ID should be {Q.format('request_id')}"))
def request_id_is(world: World, request_id: str) -> None:
    assert world.response.headers[REQUEST_ID] == request_id


@then(parsers.re(f"the response request ID should not be {Q.format('request_id')}"))
def request_id_is_not(world: World, request_id: str) -> None:
    assert world.response.headers[REQUEST_ID] != request_id


@then(parsers.re(f"the logs for this request should carry request ID {Q.format('request_id')}"))
def logs_carry_request_id(caplog: pytest.LogCaptureFixture, request_id: str) -> None:
    access = [r for r in caplog.records if r.name == "taskmanager.access"]
    assert access, "no access log line was written"
    assert getattr(access[-1], "request_id", None) == request_id


@then(parsers.re(f"the preflight should allow header {Q.format('header')}"))
def preflight_allows(world: World, header: str) -> None:
    allowed = world.response.headers.get("access-control-allow-headers", "").lower()
    assert header.lower() in allowed, world.response.headers


@then("the request ID header should be exposed to the browser")
def request_id_exposed(world: World) -> None:
    # Exposed headers appear on actual responses, not preflights; check the configured CORS policy.
    response = world.client.get("/health", headers={"Origin": "http://localhost:5173"})
    exposed = response.headers.get("access-control-expose-headers", "").lower()
    assert REQUEST_ID.lower() in exposed, response.headers


DOCUMENTATION_PATHS = ("/docs", "/redoc", "/openapi.json")


def _run_in_production(world: World, settings: Settings, **overrides: object) -> None:
    production = settings.model_copy(update={"environment": "production", **overrides})
    world.client = TestClient(create_app(production, container=world.container))


@given("the API runs in production")
def runs_in_production(world: World, test_settings: Settings) -> None:
    _run_in_production(world, test_settings)


@given("the API runs in production with documentation enabled")
def runs_in_production_with_docs(world: World, test_settings: Settings) -> None:
    _run_in_production(world, test_settings, api_docs_enabled=True)


@when("I open the API documentation")
def open_documentation(world: World) -> None:
    world.responses.extend(world.client.get(path) for path in DOCUMENTATION_PATHS)


@then("the API documentation should be available")
def documentation_available(world: World) -> None:
    statuses = [response.status_code for response in world.responses[-len(DOCUMENTATION_PATHS) :]]
    assert statuses == [200] * len(DOCUMENTATION_PATHS)


@then("the API documentation should not be found")
def documentation_not_found(world: World) -> None:
    statuses = [response.status_code for response in world.responses[-len(DOCUMENTATION_PATHS) :]]
    assert statuses == [404] * len(DOCUMENTATION_PATHS)

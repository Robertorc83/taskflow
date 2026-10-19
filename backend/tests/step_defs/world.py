"""The shared state ("world") of an acceptance scenario.

Steps talk to the running application only through HTTP, exactly like a real client. The single
exception is arranging state that has no public API (e.g. deactivating a user), which goes through
the application's own Unit of Work.
"""

from collections.abc import Awaitable, Callable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx2 as httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from taskmanager.infrastructure.config import Settings
from taskmanager.infrastructure.container import Container
from taskmanager.presentation.app import create_app
from tests.fakes import FixedClock, RecordingNotifier, SpyEventPublisher

DEFAULT_PASSWORD = "Password123!"
API = "/api/v1"


@dataclass
class World:
    app: FastAPI
    client: TestClient
    clock: FixedClock
    events: SpyEventPublisher
    notifier: RecordingNotifier | None = None
    passwords: dict[str, str] = field(default_factory=dict)
    user_ids: dict[str, str] = field(default_factory=dict)
    access_tokens: dict[str, str] = field(default_factory=dict)
    refresh_tokens: dict[str, str] = field(default_factory=dict)
    current_email: str | None = None
    responses: list[httpx.Response] = field(default_factory=list)
    task_id: str | None = None
    timezone: str | None = None

    @property
    def container(self) -> Container:
        container: Container = self.app.state.container
        return container

    @property
    def response(self) -> httpx.Response:
        assert self.responses, "No request has been made yet"
        return self.responses[-1]

    @property
    def body(self) -> Any:
        return self.response.json()

    def request(
        self,
        method: str,
        path: str,
        *,
        as_user: str | None = None,
        anonymous: bool = False,
        **kwargs: Any,
    ) -> httpx.Response:
        headers = dict(kwargs.pop("headers", {}))
        if self.timezone:
            headers["X-Timezone"] = self.timezone
        email = as_user or self.current_email
        if not anonymous and email is not None:
            headers["Authorization"] = f"Bearer {self.access_tokens[email]}"
        response = self.client.request(method, f"{API}{path}", headers=headers, **kwargs)
        self.responses.append(response)
        return response

    def ensure_user(self, email: str, password: str = DEFAULT_PASSWORD) -> str:
        if email not in self.user_ids:
            response = self.client.post(
                f"{API}/auth/register",
                json={
                    "email": email,
                    "full_name": email.split("@", maxsplit=1)[0].title(),
                    "password": password,
                },
            )
            assert response.status_code == 201, response.text
            self.user_ids[email] = response.json()["id"]
            self.passwords[email] = password
        return self.user_ids[email]

    def log_in(self, email: str) -> None:
        self.ensure_user(email)
        response = self.client.post(
            f"{API}/auth/login", json={"email": email, "password": self.passwords[email]}
        )
        assert response.status_code == 200, response.text
        self.access_tokens[email] = response.json()["access_token"]
        self.refresh_tokens[email] = response.json()["refresh_token"]
        self.current_email = email

    def run[T](self, func: Callable[..., Awaitable[T]], *args: Any) -> T:
        """Run a coroutine function on the application's event loop."""
        assert self.client.portal is not None
        return self.client.portal.call(func, *args)


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock(datetime(2026, 10, 19, 9, 0, tzinfo=UTC))


@pytest.fixture
def event_spy() -> SpyEventPublisher:
    return SpyEventPublisher()


@pytest.fixture
def app(
    test_settings: Settings, clock: FixedClock, event_spy: SpyEventPublisher, clean_database: None
) -> FastAPI:
    container = Container.build(test_settings)
    container.clock = clock
    container.event_publisher = event_spy
    return create_app(test_settings, container=container)


@pytest.fixture
def world(app: FastAPI, clock: FixedClock, event_spy: SpyEventPublisher) -> Iterator[World]:
    with TestClient(app) as client:
        yield World(app=app, client=client, clock=clock, events=event_spy)

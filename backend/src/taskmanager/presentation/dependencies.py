"""FastAPI dependency wiring: builds use cases from the container for each request."""

from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from taskmanager.application.dto import UserDTO
from taskmanager.application.exceptions import AuthenticationError, InvalidInputError
from taskmanager.application.ports import Clock
from taskmanager.application.use_cases.auth import (
    AuthenticateAccessToken,
    AuthenticateUser,
    RefreshTokens,
    RegisterUser,
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
from taskmanager.application.use_cases.users import ListUsers
from taskmanager.infrastructure.clock import ZonedClock
from taskmanager.infrastructure.container import Container

_bearer = HTTPBearer(auto_error=False, description="Paste the `access_token` from /auth/login")


def get_container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


ContainerDep = Annotated[Container, Depends(get_container)]


async def get_current_user(
    container: ContainerDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> UserDTO:
    if credentials is None:
        raise AuthenticationError("Not authenticated")
    use_case = AuthenticateAccessToken(container.unit_of_work(), container.token_service)
    return await use_case.execute(credentials.credentials)


CurrentUser = Annotated[UserDTO, Depends(get_current_user)]


def request_clock(
    container: ContainerDep,
    x_timezone: Annotated[
        str | None,
        Header(
            alias="X-Timezone",
            description="IANA time zone (e.g. America/New_York) that defines the user's "
            '"today" for due dates. Defaults to UTC.',
        ),
    ] = None,
) -> Clock:
    """The application clock, expressed in the caller's time zone (CR-005)."""
    if not x_timezone:
        return container.clock
    try:
        return ZonedClock(container.clock, ZoneInfo(x_timezone))
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise InvalidInputError("Unknown time zone", field="X-Timezone") from error


RequestClock = Annotated[Clock, Depends(request_clock)]


# ------------------------------------------------------------------ rate limiting


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


async def limit_auth(request: Request, container: ContainerDep) -> None:
    await container.rate_limiter.hit_auth(_client_ip(request))


async def limit_api(user: CurrentUser, container: ContainerDep) -> None:
    await container.rate_limiter.hit_api(str(user.id))


# ------------------------------------------------------------------ use cases


def register_user(c: ContainerDep) -> RegisterUser:
    return RegisterUser(c.unit_of_work(), c.password_hasher, c.clock)


def authenticate_user(c: ContainerDep) -> AuthenticateUser:
    return AuthenticateUser(c.unit_of_work(), c.password_hasher, c.token_service)


def refresh_tokens(c: ContainerDep) -> RefreshTokens:
    return RefreshTokens(c.unit_of_work(), c.token_service)


def list_users(c: ContainerDep) -> ListUsers:
    return ListUsers(c.unit_of_work())


def create_task(c: ContainerDep, clock: RequestClock) -> CreateTask:
    return CreateTask(c.unit_of_work(), clock, c.event_publisher)


def get_task(c: ContainerDep, clock: RequestClock) -> GetTask:
    return GetTask(c.unit_of_work(), clock)


def list_tasks(c: ContainerDep, clock: RequestClock) -> ListTasks:
    return ListTasks(c.unit_of_work(), clock)


def update_task(c: ContainerDep, clock: RequestClock) -> UpdateTask:
    return UpdateTask(c.unit_of_work(), clock)


def delete_task(c: ContainerDep, clock: RequestClock) -> DeleteTask:
    return DeleteTask(c.unit_of_work(), clock)


def assign_task(c: ContainerDep, clock: RequestClock) -> AssignTask:
    return AssignTask(c.unit_of_work(), clock, c.event_publisher)


def complete_task(c: ContainerDep, clock: RequestClock) -> CompleteTask:
    return CompleteTask(c.unit_of_work(), clock, c.event_publisher)


def reopen_task(c: ContainerDep, clock: RequestClock) -> ReopenTask:
    return ReopenTask(c.unit_of_work(), clock)

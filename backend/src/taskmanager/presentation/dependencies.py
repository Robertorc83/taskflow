"""FastAPI dependency wiring: builds use cases from the container for each request."""

from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from taskmanager.application.dto import UserDTO
from taskmanager.application.exceptions import AuthenticationError
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
    UpdateTask,
)
from taskmanager.application.use_cases.users import ListUsers
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


def create_task(c: ContainerDep) -> CreateTask:
    return CreateTask(c.unit_of_work(), c.clock, c.event_publisher)


def get_task(c: ContainerDep) -> GetTask:
    return GetTask(c.unit_of_work(), c.clock)


def list_tasks(c: ContainerDep) -> ListTasks:
    return ListTasks(c.unit_of_work(), c.clock)


def update_task(c: ContainerDep) -> UpdateTask:
    return UpdateTask(c.unit_of_work(), c.clock)


def delete_task(c: ContainerDep) -> DeleteTask:
    return DeleteTask(c.unit_of_work(), c.clock)


def assign_task(c: ContainerDep) -> AssignTask:
    return AssignTask(c.unit_of_work(), c.clock, c.event_publisher)


def complete_task(c: ContainerDep) -> CompleteTask:
    return CompleteTask(c.unit_of_work(), c.clock, c.event_publisher)

"""HTTP request/response models. They validate *shape*; business rules live in the domain."""

from datetime import date, datetime
from typing import Any, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from taskmanager.application.dto import (
    PageRequest,
    TaskDTO,
    TaskFilters,
    TaskOrdering,
    TaskScope,
    TokenPair,
    UserDTO,
    UserSummary,
)
from taskmanager.domain.entities.task import DESCRIPTION_MAX_LENGTH, TITLE_MAX_LENGTH
from taskmanager.domain.entities.user import FULL_NAME_MAX_LENGTH
from taskmanager.domain.value_objects import TaskStatus

# ------------------------------------------------------------------ errors


class FieldError(BaseModel):
    field: str
    message: str


class Problem(BaseModel):
    """RFC 9457 problem details."""

    type: str = "about:blank"
    title: str
    status: int
    detail: str | None = None
    errors: list[FieldError] | None = None


# ------------------------------------------------------------------ auth & users


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=FULL_NAME_MAX_LENGTH)
    password: str = Field(min_length=8, max_length=128)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"email": "dana@example.com", "full_name": "Dana Lee", "password": "Secret123!"}
            ]
        }
    )


class LoginRequest(BaseModel):
    email: str = Field(max_length=320)
    password: str = Field(max_length=128)

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"email": "alice@example.com", "password": "Alice123!"}]}
    )


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105 — OAuth2 token type, not a secret
    expires_in: int

    @classmethod
    def from_dto(cls, pair: TokenPair) -> Self:
        return cls(
            access_token=pair.access_token,
            refresh_token=pair.refresh_token,
            expires_in=pair.expires_in,
        )


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str
    is_active: bool
    created_at: datetime

    @classmethod
    def from_dto(cls, user: UserDTO) -> Self:
        return cls.model_validate(user)


class UserSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str


# ------------------------------------------------------------------ tasks


class TaskCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=TITLE_MAX_LENGTH)
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)
    due_date: date | None = None
    assignee_id: UUID | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"title": "Write report", "description": "Q3 numbers", "due_date": "2026-11-01"}
            ]
        }
    )


class TaskUpdateRequest(BaseModel):
    """Partial update: omitted fields are untouched; `null` clears description/due_date."""

    title: str | None = Field(default=None, min_length=1, max_length=TITLE_MAX_LENGTH)
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)
    due_date: date | None = None
    status: Literal[TaskStatus.PENDING, TaskStatus.IN_PROGRESS] | None = Field(
        default=None, description="Use POST /tasks/{id}/complete to complete a task."
    )

    @model_validator(mode="after")
    def _reject_null_for_required_fields(self) -> Self:
        for name in ("title", "status"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self

    def changes(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in self.model_fields_set}


class TaskAssignRequest(BaseModel):
    assignee_id: UUID | None = Field(description="User to assign, or null to unassign.")


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None
    status: TaskStatus
    due_date: date | None
    is_overdue: bool
    owner: UserSummaryResponse
    assignee: UserSummaryResponse | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None

    @classmethod
    def from_dto(cls, task: TaskDTO) -> Self:
        return cls.model_validate(task)


class TaskListQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scope: TaskScope = TaskScope.ALL
    status: TaskStatus | None = None
    due_from: date | None = None
    due_to: date | None = None
    ordering: TaskOrdering = TaskOrdering.CREATED_AT_DESC
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=PageRequest.MAX_SIZE)

    def filters(self) -> TaskFilters:
        return TaskFilters(
            scope=self.scope,
            status=self.status,
            due_from=self.due_from,
            due_to=self.due_to,
            ordering=self.ordering,
        )

    def page_request(self) -> PageRequest:
        return PageRequest(page=self.page, size=self.size)


class PaginationQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=PageRequest.MAX_SIZE)

    def page_request(self) -> PageRequest:
        return PageRequest(page=self.page, size=self.size)


class PageResponse[T](BaseModel):
    items: list[T]
    total: int
    page: int
    size: int
    pages: int


__all__ = [
    "FieldError",
    "LoginRequest",
    "PageResponse",
    "PaginationQuery",
    "Problem",
    "RefreshRequest",
    "RegisterRequest",
    "TaskAssignRequest",
    "TaskCreateRequest",
    "TaskListQuery",
    "TaskResponse",
    "TaskUpdateRequest",
    "TokenResponse",
    "UserResponse",
    "UserSummary",
    "UserSummaryResponse",
]

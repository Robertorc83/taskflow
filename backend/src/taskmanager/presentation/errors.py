"""Translate domain/application exceptions into RFC 9457 problem responses."""

import logging
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from taskmanager.application.exceptions import (
    ApplicationError,
    AuthenticationError,
    ConflictError,
    InvalidInputError,
    NotFoundError,
    PermissionDeniedError,
)
from taskmanager.domain.exceptions import DomainError, TaskAlreadyCompletedError
from taskmanager.infrastructure.rate_limit import RateLimitExceededError
from taskmanager.presentation.schemas import FieldError, Problem

logger = logging.getLogger(__name__)

# Most specific first: the first matching class wins.
STATUS_BY_ERROR: list[tuple[type[Exception], HTTPStatus]] = [
    (AuthenticationError, HTTPStatus.UNAUTHORIZED),
    (PermissionDeniedError, HTTPStatus.FORBIDDEN),
    (NotFoundError, HTTPStatus.NOT_FOUND),
    (ConflictError, HTTPStatus.CONFLICT),
    (TaskAlreadyCompletedError, HTTPStatus.CONFLICT),
    (InvalidInputError, HTTPStatus.UNPROCESSABLE_ENTITY),
    (DomainError, HTTPStatus.UNPROCESSABLE_ENTITY),
]


def problem_response(
    status: HTTPStatus,
    detail: str | None = None,
    *,
    errors: list[FieldError] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    problem = Problem(title=status.phrase, status=status.value, detail=detail, errors=errors)
    return JSONResponse(
        problem.model_dump(exclude_none=True),
        status_code=status.value,
        media_type="application/problem+json",
        headers=headers,
    )


def _status_for(error: Exception) -> HTTPStatus:
    return next(status for kind, status in STATUS_BY_ERROR if isinstance(error, kind))


async def _handle_business_error(_: Request, error: DomainError | ApplicationError) -> JSONResponse:
    status = _status_for(error)
    errors = None
    if isinstance(error, InvalidInputError) and error.field:
        errors = [FieldError(field=error.field, message=error.message)]
    headers = {"WWW-Authenticate": "Bearer"} if status is HTTPStatus.UNAUTHORIZED else None
    return problem_response(status, error.message, errors=errors, headers=headers)


async def _handle_validation_error(_: Request, error: RequestValidationError) -> JSONResponse:
    errors = [
        FieldError(
            field=".".join(str(part) for part in e["loc"][1:]) or str(e["loc"][0]),
            message=e["msg"],
        )
        for e in error.errors()
    ]
    return problem_response(
        HTTPStatus.UNPROCESSABLE_ENTITY, "The request is invalid", errors=errors
    )


async def _handle_rate_limit(_: Request, error: RateLimitExceededError) -> JSONResponse:
    return problem_response(
        HTTPStatus.TOO_MANY_REQUESTS,
        str(error),
        headers={"Retry-After": str(error.retry_after)},
    )


async def _handle_http_error(_: Request, error: HTTPException) -> JSONResponse:
    headers = dict(error.headers) if error.headers else None
    return problem_response(HTTPStatus(error.status_code), str(error.detail), headers=headers)


async def _handle_unexpected(_: Request, error: Exception) -> JSONResponse:
    logger.exception("Unhandled error", exc_info=error)
    return problem_response(HTTPStatus.INTERNAL_SERVER_ERROR, "An unexpected error occurred")


def register_error_handlers(app: FastAPI) -> None:
    app.exception_handler(DomainError)(_handle_business_error)
    app.exception_handler(ApplicationError)(_handle_business_error)
    app.exception_handler(RequestValidationError)(_handle_validation_error)
    app.exception_handler(RateLimitExceededError)(_handle_rate_limit)
    app.exception_handler(HTTPException)(_handle_http_error)
    app.exception_handler(Exception)(_handle_unexpected)


ERROR_RESPONSES: dict[int | str, dict[str, object]] = {
    status: {"model": Problem, "description": HTTPStatus(status).phrase}
    for status in (401, 403, 404, 409, 422, 429)
}
"""OpenAPI documentation for the problem responses an endpoint may return."""


def error_responses(*statuses: int) -> dict[int | str, dict[str, object]]:
    return {status: ERROR_RESPONSES[status] for status in statuses}

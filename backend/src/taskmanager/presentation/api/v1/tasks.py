from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from taskmanager.application.dto import CreateTaskCommand, UpdateTaskCommand
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
from taskmanager.presentation import dependencies as deps
from taskmanager.presentation.errors import error_responses
from taskmanager.presentation.schemas import (
    PageResponse,
    TaskAssignRequest,
    TaskCreateRequest,
    TaskListQuery,
    TaskResponse,
    TaskUpdateRequest,
)

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
    dependencies=[Depends(deps.limit_api)],
    responses=error_responses(401, 422, 429),
)


@router.get("", summary="List tasks I own or am assigned to")
async def list_tasks(
    user: deps.CurrentUser,
    query: Annotated[TaskListQuery, Query()],
    use_case: Annotated[ListTasks, Depends(deps.list_tasks)],
) -> PageResponse[TaskResponse]:
    page = await use_case.execute(user.id, query.filters(), query.page_request())
    return PageResponse[TaskResponse].from_page(page, TaskResponse.from_dto)


@router.post("", status_code=status.HTTP_201_CREATED, summary="Create a task")
async def create_task(
    user: deps.CurrentUser,
    body: TaskCreateRequest,
    use_case: Annotated[CreateTask, Depends(deps.create_task)],
) -> TaskResponse:
    command = CreateTaskCommand(**body.model_dump())
    return TaskResponse.from_dto(await use_case.execute(user.id, command))


@router.get("/{task_id}", responses=error_responses(404), summary="Get a task")
async def get_task(
    user: deps.CurrentUser,
    task_id: UUID,
    use_case: Annotated[GetTask, Depends(deps.get_task)],
) -> TaskResponse:
    return TaskResponse.from_dto(await use_case.execute(user.id, task_id))


@router.patch(
    "/{task_id}",
    responses=error_responses(403, 404),
    summary="Update a task (owner only)",
)
async def update_task(
    user: deps.CurrentUser,
    task_id: UUID,
    body: TaskUpdateRequest,
    use_case: Annotated[UpdateTask, Depends(deps.update_task)],
) -> TaskResponse:
    command = UpdateTaskCommand(**body.changes())
    return TaskResponse.from_dto(await use_case.execute(user.id, task_id, command))


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(403, 404),
    summary="Delete a task (owner only)",
)
async def delete_task(
    user: deps.CurrentUser,
    task_id: UUID,
    use_case: Annotated[DeleteTask, Depends(deps.delete_task)],
) -> Response:
    await use_case.execute(user.id, task_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put(
    "/{task_id}/assignee",
    responses=error_responses(403, 404),
    summary="Assign or unassign a task (owner only)",
)
async def assign_task(
    user: deps.CurrentUser,
    task_id: UUID,
    body: TaskAssignRequest,
    use_case: Annotated[AssignTask, Depends(deps.assign_task)],
) -> TaskResponse:
    return TaskResponse.from_dto(await use_case.execute(user.id, task_id, body.assignee_id))


@router.post(
    "/{task_id}/complete",
    responses=error_responses(404, 409),
    summary="Mark a task as completed (owner or assignee)",
)
async def complete_task(
    user: deps.CurrentUser,
    task_id: UUID,
    use_case: Annotated[CompleteTask, Depends(deps.complete_task)],
) -> TaskResponse:
    return TaskResponse.from_dto(await use_case.execute(user.id, task_id))


@router.post(
    "/{task_id}/reopen",
    responses=error_responses(403, 404, 409),
    summary="Reopen a completed task (owner or assignee)",
)
async def reopen_task(
    user: deps.CurrentUser,
    task_id: UUID,
    use_case: Annotated[ReopenTask, Depends(deps.reopen_task)],
) -> TaskResponse:
    return TaskResponse.from_dto(await use_case.execute(user.id, task_id))

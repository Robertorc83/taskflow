from typing import Annotated

from fastapi import APIRouter, Depends, Query

from taskmanager.application.use_cases.users import ListUsers
from taskmanager.presentation import dependencies as deps
from taskmanager.presentation.errors import error_responses
from taskmanager.presentation.schemas import PageResponse, PaginationQuery, UserResponse

router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(deps.limit_api)],
    responses=error_responses(401, 429),
)


@router.get("/me", summary="The authenticated user")
async def me(user: deps.CurrentUser) -> UserResponse:
    return UserResponse.from_dto(user)


@router.get("", responses=error_responses(422), summary="List users (e.g. for assignment)")
async def list_users(
    query: Annotated[PaginationQuery, Query()],
    use_case: Annotated[ListUsers, Depends(deps.list_users)],
) -> PageResponse[UserResponse]:
    page = await use_case.execute(query.page_request())
    return PageResponse[UserResponse].from_page(page, UserResponse.from_dto)

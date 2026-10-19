from typing import Annotated

from fastapi import APIRouter, Depends, status

from taskmanager.application.dto import RegisterUserCommand
from taskmanager.application.use_cases.auth import AuthenticateUser, RefreshTokens, RegisterUser
from taskmanager.presentation import dependencies as deps
from taskmanager.presentation.errors import error_responses
from taskmanager.presentation.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    dependencies=[Depends(deps.limit_auth)],
    responses=error_responses(422, 429),
)


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(409),
    summary="Create an account",
)
async def register(
    body: RegisterRequest, use_case: Annotated[RegisterUser, Depends(deps.register_user)]
) -> UserResponse:
    user = await use_case.execute(
        RegisterUserCommand(email=body.email, full_name=body.full_name, password=body.password)
    )
    return UserResponse.from_dto(user)


@router.post("/login", responses=error_responses(401), summary="Exchange credentials for tokens")
async def login(
    body: LoginRequest, use_case: Annotated[AuthenticateUser, Depends(deps.authenticate_user)]
) -> TokenResponse:
    return TokenResponse.from_dto(await use_case.execute(body.email, body.password))


@router.post("/refresh", responses=error_responses(401), summary="Exchange a refresh token")
async def refresh(
    body: RefreshRequest, use_case: Annotated[RefreshTokens, Depends(deps.refresh_tokens)]
) -> TokenResponse:
    return TokenResponse.from_dto(await use_case.execute(body.refresh_token))

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from taskmanager.infrastructure.config import Settings, get_settings
from taskmanager.infrastructure.container import Container
from taskmanager.presentation.api.v1 import auth, tasks, users
from taskmanager.presentation.dependencies import ContainerDep
from taskmanager.presentation.errors import register_error_handlers

DESCRIPTION = """
Task management API: create, assign, complete and filter tasks.

**Authentication:** register (or use a demo account when demo data is enabled — see README),
call `POST /api/v1/auth/login`, then click **Authorize** and paste the `access_token`.

**Time zones:** send `X-Timezone: <IANA zone>` so due dates and "overdue" follow your calendar.

Errors follow [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457) (`application/problem+json`).
"""


def create_app(settings: Settings | None = None, *, container: Container | None = None) -> FastAPI:
    settings = settings or get_settings()
    container = container or Container.build(settings)
    logging.basicConfig(level=settings.log_level)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await container.aclose()

    app = FastAPI(
        title="Task Manager API",
        version="1.0.0",
        description=DESCRIPTION,
        lifespan=lifespan,
    )
    app.state.container = container

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["Authorization", "Content-Type"],
        expose_headers=["Retry-After"],
    )
    register_error_handlers(app)

    for router in (auth.router, users.router, tasks.router):
        app.include_router(router, prefix="/api/v1")

    @app.get("/health", tags=["ops"], summary="Liveness and database connectivity")
    async def health(c: ContainerDep) -> dict[str, str]:
        await c.check_database()
        return {"status": "ok"}

    return app

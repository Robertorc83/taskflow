from collections.abc import Callable, Iterable
from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement, Select, UnaryExpression, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from taskmanager.application.dto import Page, PageRequest, TaskFilters, TaskOrdering, TaskScope
from taskmanager.domain.entities import Task, User
from taskmanager.infrastructure.db.models import TaskModel, UserModel

# ------------------------------------------------------------------ mapping


def _user_to_entity(row: UserModel) -> User:
    return User(
        id=row.id,
        email=row.email,
        full_name=row.full_name,
        hashed_password=row.hashed_password,
        is_active=row.is_active,
        created_at=row.created_at,
    )


def _user_to_row(user: User, row: UserModel | None = None) -> UserModel:
    row = row or UserModel(id=user.id)
    row.email = user.email
    row.full_name = user.full_name
    row.hashed_password = user.hashed_password
    row.is_active = user.is_active
    row.created_at = user.created_at
    return row


def _task_to_entity(row: TaskModel) -> Task:
    return Task(
        id=row.id,
        title=row.title,
        description=row.description,
        status=row.status,
        due_date=row.due_date,
        owner_id=row.owner_id,
        assignee_id=row.assignee_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        completed_at=row.completed_at,
    )


def _task_to_row(task: Task, row: TaskModel | None = None) -> TaskModel:
    row = row or TaskModel(id=task.id)
    row.title = task.title
    row.description = task.description
    row.status = task.status
    row.due_date = task.due_date
    row.owner_id = task.owner_id
    row.assignee_id = task.assignee_id
    row.created_at = task.created_at
    row.updated_at = task.updated_at
    row.completed_at = task.completed_at
    return row


async def _paginate[M, E](
    session: AsyncSession, query: Select[M], page: PageRequest, to_entity: Callable[[M], E]
) -> Page[E]:
    total = await session.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    rows = await session.scalars(query.offset(page.offset).limit(page.size))
    return Page(
        items=[to_entity(row) for row in rows], total=total or 0, page=page.page, size=page.size
    )


# ------------------------------------------------------------------ repositories


class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user: User) -> None:
        self._session.add(_user_to_row(user))

    async def save(self, user: User) -> None:
        _user_to_row(user, await self._session.get(UserModel, user.id))

    async def get(self, user_id: UUID) -> User | None:
        row = await self._session.get(UserModel, user_id)
        return _user_to_entity(row) if row else None

    async def get_by_email(self, email: str) -> User | None:
        row = await self._session.scalar(select(UserModel).where(UserModel.email == email))
        return _user_to_entity(row) if row else None

    async def get_many(self, user_ids: Iterable[UUID]) -> dict[UUID, User]:
        ids = set(user_ids)
        if not ids:
            return {}
        rows = await self._session.scalars(select(UserModel).where(UserModel.id.in_(ids)))
        return {row.id: _user_to_entity(row) for row in rows}

    async def list(self, page: PageRequest) -> Page[User]:
        query = select(UserModel).order_by(UserModel.full_name, UserModel.id)
        return await _paginate(self._session, query, page, _user_to_entity)


class SqlAlchemyTaskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, task: Task) -> None:
        self._session.add(_task_to_row(task))

    async def save(self, task: Task) -> None:
        _task_to_row(task, await self._session.get(TaskModel, task.id))

    async def get(self, task_id: UUID) -> Task | None:
        row = await self._session.get(TaskModel, task_id)
        return _task_to_entity(row) if row else None

    async def delete(self, task: Task) -> None:
        await self._session.execute(delete(TaskModel).where(TaskModel.id == task.id))

    async def list_visible_to(
        self, user_id: UUID, filters: TaskFilters, page: PageRequest
    ) -> Page[Task]:
        query = (
            select(TaskModel)
            .where(*self._conditions(user_id, filters))
            .order_by(*self._ordering(filters.ordering))
        )
        return await _paginate(self._session, query, page, _task_to_entity)

    @staticmethod
    def _conditions(user_id: UUID, filters: TaskFilters) -> list[ColumnElement[bool]]:
        scope = {
            TaskScope.ALL: or_(TaskModel.owner_id == user_id, TaskModel.assignee_id == user_id),
            TaskScope.OWNED: TaskModel.owner_id == user_id,
            TaskScope.ASSIGNED: TaskModel.assignee_id == user_id,
        }[filters.scope]
        conditions = [scope]
        if filters.status is not None:
            conditions.append(TaskModel.status == filters.status)
        if filters.due_from is not None:
            conditions.append(TaskModel.due_date >= filters.due_from)
        if filters.due_to is not None:
            conditions.append(TaskModel.due_date <= filters.due_to)
        return conditions

    @staticmethod
    def _ordering(ordering: TaskOrdering) -> list[UnaryExpression[Any]]:
        orderings: dict[TaskOrdering, UnaryExpression[Any]] = {
            TaskOrdering.CREATED_AT: TaskModel.created_at.asc(),
            TaskOrdering.CREATED_AT_DESC: TaskModel.created_at.desc(),
            TaskOrdering.DUE_DATE: TaskModel.due_date.asc().nulls_last(),
            TaskOrdering.DUE_DATE_DESC: TaskModel.due_date.desc().nulls_last(),
        }
        # Stable tie-breakers keep pages consistent between requests (SPEC-003 R7).
        return [orderings[ordering], TaskModel.created_at.desc(), TaskModel.id.asc()]

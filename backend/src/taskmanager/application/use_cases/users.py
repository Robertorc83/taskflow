from taskmanager.application.dto import Page, PageRequest, UserDTO
from taskmanager.application.ports import UnitOfWork


class ListUsers:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, page: PageRequest) -> Page[UserDTO]:
        async with self._uow as uow:
            users = await uow.users.list(page)
        return users.map(UserDTO.from_entity)

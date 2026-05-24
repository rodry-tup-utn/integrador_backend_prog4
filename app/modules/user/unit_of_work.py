from app.core.unit_of_work import UnitOfWork
from sqlmodel import Session
from app.modules.user.repositories.user_repository import UserRepository
from app.modules.user.repositories.role_repository import RoleRepository
from app.modules.user.repositories.user_role_repository import UserRoleLinkRepository
from app.modules.user.repositories.address_repository import (
    AddressRepository,
)


class UserUnitOfWork(UnitOfWork["UserUnitOfWork"]):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.users = UserRepository(session)
        self.roles = RoleRepository(session)
        self.user_role = UserRoleLinkRepository(session)
        self.delivery_adress = AddressRepository(session)

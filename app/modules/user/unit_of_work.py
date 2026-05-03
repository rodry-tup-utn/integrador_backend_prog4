from app.core.unit_of_work import UnitOfWork
from sqlmodel import Session
from app.modules.user.repository import UserRepository


class UserUnitOfWork(UnitOfWork["UserUnitOfWork"]):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.users = UserRepository(session)

from app.core.unit_of_work import UnitOfWork
from sqlmodel import Session
from app.modules.auth.repository import RefreshTokenRepository


class AuthUnitOfWork(UnitOfWork["AuthUnitOfWork"]):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.refresh_tokens = RefreshTokenRepository(session)

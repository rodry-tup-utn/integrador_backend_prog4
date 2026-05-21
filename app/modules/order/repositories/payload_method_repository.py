from sqlmodel import Session, select
from app.core.repository import BaseRepository
from app.modules.order.models import PayloadMethod
from typing import Sequence


class PayloadMethodRepository(BaseRepository["PayloadMethod"]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, PayloadMethod)

    def get_by_code(self, code: str) -> PayloadMethod | None:
        statement = select(PayloadMethod).where(PayloadMethod.code == code)
        return self.session.exec(statement).first()

    def get_available(self) -> Sequence[PayloadMethod]:
        statement = select(PayloadMethod).where(PayloadMethod.available == True)
        return self.session.exec(statement).all()

from sqlmodel import Session, select, col, update, func
from app.modules.user.models import Address
from app.core.repository import BaseRepository
from typing import List
from datetime import datetime, timezone


class AddressRepository(BaseRepository["Address"]):
    """Repositorio de Direcciones de Entrega"""

    def __init__(
        self,
        session: Session,
    ) -> None:
        super().__init__(session, Address)

    def get_by_id(self, id: int) -> Address | None:
        statement = select(Address).where(Address.id == id)

        return self.session.exec(statement).first()

    def get_by_user_id(self, user_id: int, only_actives: bool = False) -> List[Address]:
        statement = select(Address).where(Address.user_id == user_id)

        if only_actives:
            statement = statement.where(col(Address.deleted_at).is_(None))

        return self.session.exec(statement).all()

    def unset_main_for_user(self, user_id: int) -> None:
        stmt = (
            update(Address)
            .where(Address.user_id == user_id, Address.is_main == True)
            .values(is_main=False, updated_at=datetime.now(timezone.utc))
        )
        self.session.exec(stmt)
        self.session.flush()

    def get_main_by_user_id(self, user_id: int) -> Address | None:
        stmt = select(Address).where(
            Address.user_id == user_id,
            Address.is_main == True,
            col(Address.deleted_at).is_(None),
        )
        return self.session.exec(stmt).first()

    def count_active_by_user_id(self, user_id: int) -> int:
        stmt = select(func.count(Address.id)).where(
            Address.user_id == user_id,
            col(Address.deleted_at).is_(None),
        )
        return self.session.exec(stmt).one()

    def soft_delete(self, adress: Address):

        adress.deleted_at = datetime.now(timezone.utc)
        self.session.add(adress)
        self.session.flush()

    def restore(self, adress: Address):
        adress.deleted_at = None
        adress.updated_at = datetime.now(timezone.utc)
        self.session.add(adress)
        self.session.flush()

        return adress

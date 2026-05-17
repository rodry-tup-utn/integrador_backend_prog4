from sqlmodel import Session, select, col
from app.modules.user.models import DeliveryAdress
from app.core.repository import BaseRepository
from typing import List
from datetime import datetime, timezone


class DeliveryAdressRepository(BaseRepository["DeliveryAdress"]):
    """Repositorio de Direcciones de Entrega"""

    def __init__(
        self,
        session: Session,
    ) -> None:
        super().__init__(session, DeliveryAdress)

    def get_by_id(self, id: int) -> DeliveryAdress | None:
        statement = select(DeliveryAdress).where(DeliveryAdress.id == id)

        return self.session.exec(statement).first()

    def get_by_user_id(
        self, user_id: int, only_actives: bool = False
    ) -> List[DeliveryAdress]:
        statement = select(DeliveryAdress).where(DeliveryAdress.user_id == user_id)

        if only_actives:
            statement = statement.where(col(DeliveryAdress.deleted_at).is_(None))

        return self.session.exec(statement).all()

    def soft_delete(self, adress: DeliveryAdress):

        adress.deleted_at = datetime.now(timezone.utc)
        self.session.add(adress)
        self.session.flush()

    def restore(self, adress: DeliveryAdress):
        adress.deleted_at = None
        adress.updated_at = datetime.now(timezone.utc)
        self.session.add(adress)
        self.session.flush()

        return adress

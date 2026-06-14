from app.modules.user.models import Address
from app.modules.user.schemas import (
    AddressRead,
    AddressCreate,
    AddressUpdate,
)
from app.modules.user.unit_of_work import UserUnitOfWork
from sqlmodel import Session
from datetime import datetime, timezone
from app.core.exceptions import (
    ResourceNotFoundError,
    AuthorizationError,
    BusinessRuleError,
)


class DeliveryAdressService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _get_active_or_404(self, uow: UserUnitOfWork, id: int) -> Address:
        address = uow.delivery_adress.get_by_id(id)
        if not address or address.deleted_at is not None:
            raise ResourceNotFoundError(resource="Domicilio", identifier=id)
        return address

    def _verify_ownership(self, address: Address, user_id: int) -> None:
        if address.user_id != user_id:
            raise AuthorizationError(
                "No tienes permisos para modificar este domicilio",
            )

    def create(self, user_id: int, data: AddressCreate) -> AddressRead:
        with UserUnitOfWork(self._session) as uow:
            address = Address(
                user_id=user_id,  # type: ignore
                alias=data.alias,
                line_one=data.line_one,
                line_two=data.line_two,
                city=data.city,
                province=data.province,
                zip_code=data.zip_code,
                latitude=data.latitude,
                longitude=data.longitude,
                is_main=data.is_main or False,
            )
            uow.delivery_adress.add(address)
            result = AddressRead.model_validate(address)
        return result

    def update(self, id: int, data: AddressUpdate, user_id: int) -> AddressRead:
        with UserUnitOfWork(self._session) as uow:
            address = self._get_active_or_404(uow, id)
            self._verify_ownership(address, user_id)
            update_data = data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(address, field, value)
            address.updated_at = datetime.now(timezone.utc)
            uow.delivery_adress.add(address)
            result = AddressRead.model_validate(address)
        return result

    def soft_delete(self, id: int, user_id: int) -> None:
        with UserUnitOfWork(self._session) as uow:
            address = self._get_active_or_404(uow, id)
            self._verify_ownership(address, user_id)
            uow.delivery_adress.soft_delete(address)

    def restore(self, id: int, user_id: int) -> AddressRead:
        with UserUnitOfWork(self._session) as uow:
            address = uow.delivery_adress.get_by_id(id)
            if not address or address.deleted_at is None:
                raise BusinessRuleError(
                    "El domicilio no se encuentra eliminado",
                )
            self._verify_ownership(address, user_id)
            uow.delivery_adress.restore(address)
            result = AddressRead.model_validate(address)
        return result

    def get_active_by_user_id(self, user_id: int) -> list[AddressRead]:
        with UserUnitOfWork(self._session) as uow:
            addresses = uow.delivery_adress.get_by_user_id(user_id, only_actives=True)
            return [AddressRead.model_validate(a) for a in addresses]

    def get_by_user_id(self, user_id: int) -> list[AddressRead]:
        with UserUnitOfWork(self._session) as uow:
            addresses = uow.delivery_adress.get_by_user_id(user_id, only_actives=False)
            return [AddressRead.model_validate(a) for a in addresses]

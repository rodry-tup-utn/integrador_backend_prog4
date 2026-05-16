from fastapi import HTTPException, status
from app.modules.user.schemas import (
    UserBase,
    UserAuthCredentials,
    UserCreate,
    UserUpdate,
    UserPrivate,
    UserList,
)
from sqlmodel import Session
from app.modules.user.unit_of_work import UserUnitOfWork
from app.modules.user.models import User, Role, UserRoleLink
from datetime import datetime, timezone
from app.core.security import get_password_hash


class UserService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _get_or_404(self, uow: UserUnitOfWork, user_id: int) -> User:
        user = uow.users.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                f"Usuario con id {user_id} no encontrado",
            )
        return user

    def _get_active_or_404(self, uow: UserUnitOfWork, user_id: int) -> User:
        user = uow.users.get_active_by_id(user_id)
        if not user:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                f"Usuario con id {user_id} no encontrado",
            )
        return user

    def _assert_email_unique(self, uow: UserUnitOfWork, email: str):
        if uow.users.exists_by_email(email):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Ya existe un usuario registrado con el email {email}",
            )

    def _get_role_by_code_or_404(self, uow: UserUnitOfWork, code: str) -> Role:
        role = uow.roles.get_by_code(code)
        if not role:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Rol {code} inexistente")
        return role

    def create(self, data: UserCreate) -> UserBase:
        with UserUnitOfWork(self._session) as uow:
            self._assert_email_unique(uow, data.email)

            hashed_pass = get_password_hash(data.password)
            user_data = data.model_dump(exclude={"password"})
            user_data["hashed_pass"] = hashed_pass

            user = User(**user_data)

            uow.users.add(user)

            result = UserBase.model_validate(user)

        return result

    def update_profile(self, user_id: int, data: UserUpdate) -> UserPrivate:
        with UserUnitOfWork(self._session) as uow:
            user = self._get_active_or_404(uow, user_id)
            update_data = data.model_dump(exclude_unset=True)

            for field, value in update_data.items():
                setattr(user, field, value)

            user.updated_at = datetime.now(timezone.utc)
            uow.users.add(user)
            result = UserPrivate.model_validate(user)

        return result

    def get_by_id(self, user_id: int) -> UserPrivate:
        with UserUnitOfWork(self._session) as uow:
            user = self._get_or_404(uow, user_id)
            result = UserPrivate.model_validate(user)

        return result

    def get_active_by_id(self, user_id: int) -> UserPrivate:
        with UserUnitOfWork(self._session) as uow:
            user = self._get_active_or_404(uow, user_id)
            result = UserPrivate.model_validate(user)
        return result

    def get_active_private(self, user_id: int) -> UserPrivate:
        with UserUnitOfWork(self._session) as uow:
            user = self._get_active_or_404(uow, user_id)
            result = UserPrivate.model_validate(user)
        return result

    def get_auth_credentials(self, email: str) -> UserAuthCredentials:
        with UserUnitOfWork(self._session) as uow:
            credentials = uow.users.get_auth_credential(email)
            if not credentials:
                raise HTTPException(
                    status.HTTP_404_NOT_FOUND, f"Usuario email {email} no encontrado"
                )
            return credentials

    def soft_delete(self, user_id: int, admin_id: int):
        if user_id == admin_id:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Un administrador no puede eliminarse a si mismo",
            )
        with UserUnitOfWork(self._session) as uow:
            user = self._get_active_or_404(uow, user_id)
            uow.users.delete(user)
        return status.HTTP_204_NO_CONTENT

    def restore(self, user_id: int) -> UserBase:
        with UserUnitOfWork(self._session) as uow:
            user = self._get_or_404(uow, user_id)
            if user.deleted_at is None:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "No se puede restaurar un usuario activo",
                )
            uow.users.restore(user)
            result = UserBase.model_validate(user)
        return result

    def get_all(self, offset: int = 0, limit: int = 20) -> UserList:
        with UserUnitOfWork(self._session) as uow:
            users = uow.users.get_all(offset, limit)
            total = uow.users.count()
            data = [UserPrivate.model_validate(u) for u in users]

            result = UserList(data=data, total=total)
        return result

    def asign_role(self, user_id: int, role_code: str, user_assing_id: int):
        with UserUnitOfWork(self._session) as uow:
            user = self._get_active_or_404(uow, user_id)
            role = self._get_role_by_code_or_404(uow, role_code)

            # verificacion de seguridad para usuario que asigna
            self._get_active_or_404(uow, user_assing_id)

            existing_link = uow.user_role.get_by_user_id_and_role_code(
                user_id, role_code
            )
            created_time = datetime.now(timezone.utc)
            # verificar si la relacion ya existe, y reactivar en caso de rol inactivos
            if existing_link:

                if existing_link.expires_at is None:
                    return existing_link

                existing_link.expires_at = None

                uow.user_role.add(existing_link)
                return existing_link

            user_role = UserRoleLink(
                user_id=user.id,  # type: ignore
                role_code=role.code,
                assigned_by_id=user_assing_id,
                created_at=created_time,
            )

            uow.user_role.add(user_role)

            return user_role

    def revoke_role(self, user_id: int, role_code: str) -> None:
        with UserUnitOfWork(self._session) as uow:
            self._get_role_by_code_or_404(uow, role_code)
            self._get_active_or_404(uow, user_id)

            user_role_link = uow.user_role.get_by_user_id_and_role_code(
                user_id, role_code
            )
            if not user_role_link:
                raise HTTPException(
                    status.HTTP_404_NOT_FOUND, "Relacion de rol no encontrada"
                )

            if user_role_link.expires_at is not None:
                raise HTTPException(
                    status.http_400, "El rol ya se encuentra desactivado"
                )

            actual_date = datetime.now(timezone.utc)
            user_role_link.expires_at = actual_date

            uow.user_role.add(user_role_link)

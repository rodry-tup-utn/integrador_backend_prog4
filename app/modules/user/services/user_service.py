from fastapi import HTTPException, status
from app.modules.user.schemas import (
    UserResponse,
    UserCreate,
    UserCreateByAdmin,
    UserUpdate,
    UserAdminRead,
    UserPaginatedRead,
    UserDetailRead,
    UserRoleRead,
    RoleRead,
    UserProfileRead,
    AddressRead,
    UserAuthData,
    UserSessionRead,
)
from sqlmodel import Session
from app.modules.user.unit_of_work import UserUnitOfWork
from app.modules.user.models import User, Role, UserRoleLink
from datetime import datetime, timezone
from app.core.security import get_password_hash

DEFAULT_ROLE = "CLIENT"


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
        user = uow.users.get_by_id(user_id, True)
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

    def create(self, data: UserCreate) -> UserResponse:
        with UserUnitOfWork(self._session) as uow:
            self._assert_email_unique(uow, data.email)

            hashed_pass = get_password_hash(data.password)
            user_data = data.model_dump(exclude={"password"})
            user_data["hashed_pass"] = hashed_pass

            user = User(**user_data)
            uow.users.add(user)

            role = self._get_role_by_code_or_404(uow, DEFAULT_ROLE)
            user_role = UserRoleLink(
                user_id=user.id,  # type: ignore
                role_code=role.code,
                assigned_by_id=user.id,  # type: ignore
                created_at=datetime.now(timezone.utc),
            )
            uow.user_role.add(user_role)

            result = UserResponse.model_validate(user)

        return result

    def create_by_admin(self, data: UserCreateByAdmin, admin_id: int) -> UserResponse:
        with UserUnitOfWork(self._session) as uow:
            self._assert_email_unique(uow, data.email)
            role = self._get_role_by_code_or_404(uow, data.role_code)

            hashed_pass = get_password_hash(data.password)
            user_data = data.model_dump(exclude={"password", "role_code"})
            user_data["hashed_pass"] = hashed_pass

            user = User(**user_data)
            uow.users.add(user)

            user_role = UserRoleLink(
                user_id=user.id,  # type: ignore
                role_code=role.code,
                assigned_by_id=admin_id,
                created_at=datetime.now(timezone.utc),
            )
            uow.user_role.add(user_role)

            result = UserResponse.model_validate(user)

        return result

    def update_profile(self, user_id: int, data: UserUpdate) -> UserAdminRead:
        with UserUnitOfWork(self._session) as uow:
            user = self._get_active_or_404(uow, user_id)
            update_data = data.model_dump(exclude_unset=True)

            for field, value in update_data.items():
                setattr(user, field, value)

            user.updated_at = datetime.now(timezone.utc)
            uow.users.add(user)
            result = UserAdminRead.model_validate(user)

        return result

    def get_by_id(self, user_id: int) -> UserDetailRead:
        with UserUnitOfWork(self._session) as uow:
            user = self._get_or_404(uow, user_id)
            result = UserDetailRead.model_validate(user)

        return result

    def get_active_by_id(self, user_id: int) -> UserDetailRead:
        with UserUnitOfWork(self._session) as uow:
            user = self._get_active_or_404(uow, user_id)
            result = UserDetailRead.model_validate(user)
        return result

    def get_active_private(self, user_id: int) -> UserAdminRead:
        with UserUnitOfWork(self._session) as uow:
            user = self._get_active_or_404(uow, user_id)
            result = UserAdminRead.model_validate(user)
        return result

    def get_auth_credentials(self, email: str) -> UserAuthData:
        with UserUnitOfWork(self._session) as uow:
            credentials = uow.users.get_auth_credential(email)
            if not credentials:
                raise HTTPException(
                    status.HTTP_404_NOT_FOUND, f"Usuario email {email} no encontrado"
                )
            return credentials

    def get_session_data(self, user_id: int) -> UserSessionRead:
        with UserUnitOfWork(self._session) as uow:
            user = uow.users.get_by_id(user_id, True)
            if not user:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")

            now = datetime.now(timezone.utc)
            active_roles = [
                link.role_code
                for link in user.roles
                if (link.expires_at is None or link.expires_at > now)
            ]
            result = UserSessionRead(
                id=user.id,  # type: ignore
                name=user.name,
                lastname=user.lastname,
                email=user.email,
                roles=active_roles,
            )
        return result

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

    def restore(self, user_id: int) -> UserResponse:
        with UserUnitOfWork(self._session) as uow:
            user = self._get_or_404(uow, user_id)
            if user.deleted_at is None:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "No se puede restaurar un usuario activo",
                )
            uow.users.restore(user)
            result = UserResponse.model_validate(user)
        return result

    def get_all(self, offset: int = 0, limit: int = 20) -> UserPaginatedRead:
        with UserUnitOfWork(self._session) as uow:
            users = uow.users.get_all(offset, limit)
            total = uow.users.count()
            data = [UserAdminRead.model_validate(u) for u in users]

            result = UserPaginatedRead(data=data, total=total)
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
                    status.HTTP_400_BAD_REQUEST, "El rol ya se encuentra desactivado"
                )

            actual_date = datetime.now(timezone.utc)
            user_role_link.expires_at = actual_date

            uow.user_role.add(user_role_link)

    def get_user_with_active_roles(self, user_id: int) -> UserDetailRead:
        with UserUnitOfWork(self._session) as uow:
            user = uow.users.get_by_id(user_id, True)
            if not user:
                raise HTTPException(status.http_404, "Usuario no encontrado")

            now = datetime.utcnow()

            active_roles = [
                UserRoleRead(
                    assigned_by_id=link.assigned_by_id,
                    expires_at=link.expires_at,
                    created_at=link.created_at,
                    role_user=RoleRead.model_validate(link.role_user),
                )
                for link in user.roles
                if (link.expires_at is None or link.expires_at > now)
            ]

            return UserDetailRead(
                id=user.id,  # type: ignore
                name=user.name,
                lastname=user.lastname,
                email=user.email,
                roles=active_roles,
            )

    def get_user_profile(self, user_id: int) -> UserProfileRead:
        with UserUnitOfWork(self._session) as uow:
            user = uow.users.get_with_roles_and_addresses(user_id, only_actives=True)

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Usuario no encontrado",
                )

            now = datetime.utcnow()

            active_roles = [
                UserRoleRead(
                    assigned_by_id=link.assigned_by_id,
                    expires_at=link.expires_at,
                    created_at=link.created_at,
                    role_user=RoleRead.model_validate(link.role_user),
                )
                for link in user.roles
                if link.expires_at is None or link.expires_at > now
            ]

            addresses_read = [
                AddressRead.model_validate(address)
                for address in user.addresses
                if address.deleted_at is None
            ]

            return UserProfileRead(
                id=user.id,  # type: ignore
                name=user.name,
                lastname=user.lastname,
                email=user.email,
                roles=active_roles,
                addresses=addresses_read,
            )

    def search(self, query: str, offset: int = 0, limit: int = 20) -> UserPaginatedRead:
        with UserUnitOfWork(self._session) as uow:
            users = uow.users.search(query, offset, limit)
            total = uow.users.count_search_results(query)

            data = [UserAdminRead.model_validate(u) for u in users]

            result = UserPaginatedRead(data=data, total=total)

        return result

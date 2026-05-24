from datetime import datetime, timezone
from sqlmodel import Session, select, col
from app.core.repository import BaseRepository
from app.modules.user.models import User
from typing import Sequence
from sqlalchemy import func, or_
from app.modules.user.schemas import UserAuthData
from sqlalchemy.orm import selectinload
from app.modules.user.models import UserRoleLink
from app.modules.user.models import Role


class UserRepository(BaseRepository["User"]):
    """Repositorio de Usuarios"""

    def __init__(self, session: Session) -> None:
        super().__init__(session, User)

    def get_all(self, offset: int = 0, limit: int = 20) -> Sequence[User]:
        statement = (
            select(User)
            .offset(offset)
            .limit(limit)
            .options(selectinload(User.roles).selectinload(UserRoleLink.role_user))
        )
        return self.session.exec(statement).all()

    def get_all_active(self, offset: int = 0, limit: int = 20) -> Sequence[User]:
        statement = (
            select(User)
            .where(col(User.deleted_at).is_(None))
            .order_by(User.name)
            .offset(offset)
            .limit(limit)
            .options(selectinload(User.roles).selectinload(UserRoleLink.role_user))
        )
        return self.session.exec(statement).all()

    def count_active(self) -> int:
        statement = (
            select(func.count()).select_from(User).where(col(User.deleted_at).is_(None))
        )
        return self.session.exec(statement).one()

    def get_by_id(self, user_id: int, only_actives=False) -> User | None:
        statement = (
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.roles).selectinload(UserRoleLink.role_user))
        )

        if only_actives:
            statement = statement.where(col(User.deleted_at).is_(None))

        return self.session.exec(statement).first()

    def get_with_roles_and_addresses(
        self, user_id: int, only_actives=False
    ) -> User | None:
        statement = (
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.roles).selectinload(UserRoleLink.role_user),
                selectinload(User.addresses),
            )
        )
        if only_actives:
            statement = statement.where(col(User.deleted_at).is_(None))

        return self.session.exec(statement).first()

    def get_by_email(self, email: str) -> User | None:
        statement = select(User).where(User.email == email)
        return self.session.exec(statement).first()

    def exists_by_email(self, email: str) -> bool:
        statement = select(User.id).where(User.email == email)
        return self.session.exec(statement).first() is not None

    def get_active_by_email(self, email: str) -> User | None:
        statement = select(User).where(
            User.email == email, col(User.deleted_at).is_(None)
        )
        return self.session.exec(statement).first()

    def soft_delete(self, user: User) -> None:
        user.deleted_at = datetime.now(timezone.utc)
        user.updated_at = datetime.now(timezone.utc)
        self.session.add(user)
        self.session.flush()

    def restore(self, user: User) -> User | None:
        user.deleted_at = None
        user.updated_at = datetime.now(timezone.utc)
        self.session.add(user)
        self.session.flush()
        return user

    def get_auth_credential(self, email: str) -> UserAuthData | None:
        statement = (
            select(User)
            .where(User.email == email, col(User.deleted_at).is_(None))
            .options(selectinload(User.roles).selectinload(UserRoleLink.role_user))
        )
        user = self.session.exec(statement).first()

        if not user:
            return None

        now = datetime.now(timezone.utc)
        # filtra solo roles que esten activos
        roles = [
            link.role_user.code
            for link in user.roles
            if link.role_user and (link.expires_at is None or link.expires_at > now)
        ]

        return UserAuthData(
            id=user.id,
            hashed_pass=user.hashed_pass,
            roles=roles,
            name=user.name,
        )

    def get_role_by_code(self, code: str):
        statement = select(Role).where(Role.code == code)

        return self.session.exec(statement).first()

    def search(self, query: str, offset: int = 0, limit: int = 20) -> Sequence[User]:
        statement = (
            select(User)
            .offset(offset)
            .limit(limit)
            .where(
                or_(
                    col(User.name).ilike(f"%{query}%"),
                    col(User.lastname).ilike(f"%{query}%"),
                    col(User.email).ilike(f"%{query}%"),
                )
            )
            .options(selectinload(User.roles).selectinload(UserRoleLink.role_user))
        )

        return self.session.exec(statement).all()

    def count_search_results(self, query: str) -> int:
        statement = (
            select(func.count())
            .select_from(User)
            .where(
                or_(
                    col(User.name).ilike(f"%{query}%"),
                    col(User.lastname).ilike(f"%{query}%"),
                    col(User.email).ilike(f"%{query}%"),
                )
            )
        )

        return self.session.exec(statement).one()

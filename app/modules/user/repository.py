from typing import Type
from datetime import datetime, timezone
from sqlmodel import Session, select, col
from app.core.repository import BaseRepository
from app.modules.user.models import User
from typing import Sequence
from sqlalchemy import func
from app.modules.user.schemas import UserAuthCredentials


class UserRepository(BaseRepository["User"]):
    """Repositorio de Usuarios"""

    def __init__(self, session: Session) -> None:
        super().__init__(session, User)

    def get_all_active(self, offset: int = 0, limit: int = 20) -> Sequence[User]:
        statement = (
            select(User)
            .where(col(User.deleted_at).is_(None))
            .order_by(User.name)
            .offset(offset)
            .limit(limit)
        )
        return self.session.exec(statement).all()

    def count_active(self) -> int:
        statement = (
            select(func.count()).select_from(User).where(col(User.deleted_at).is_(None))
        )
        return self.session.exec(statement).one()

    def get_active_by_id(self, user_id: int) -> User | None:
        statement = (
            select(User).where(col(User.deleted_at).is_(None)).where(User.id == user_id)
        )
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

    def get_auth_credential(self, email: str) -> UserAuthCredentials | None:
        statement = select(User.id, User.role, User.hashed_pass, User.email).where(
            User.email == email, col(User.deleted_at).is_(None)
        )
        row = self.session.exec(statement).first()

        if not row:
            return None

        return UserAuthCredentials(
            id=row.id, hashed_pass=row.hashed_pass, role=row.role, email=row.email
        )

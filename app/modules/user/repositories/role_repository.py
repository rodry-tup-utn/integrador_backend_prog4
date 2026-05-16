from sqlmodel import Session, select
from app.modules.user.models import Role
from app.core.repository import BaseRepository


class RoleRepository(BaseRepository["Role"]):
    """Repositorio de Roles"""

    def __init__(
        self,
        session: Session,
    ) -> None:
        super().__init__(session, Role)

    def get_by_code(self, code: str) -> Role | None:
        statement = select(Role).where(Role.code == code)

        return self.session.exec(statement).first()

from sqlmodel import select
from sqlmodel import Session

from app.modules.user.models import UserRoleLink
from app.core.repository import BaseRepository


class UserRoleLinkRepository(BaseRepository["UserRoleLink"]):
    """Repositorio User Role Link"""

    def __init__(self, session: Session) -> None:
        super().__init__(session, UserRoleLink)

    def get_by_user_id_and_role_code(
        self, user_id: int, role_code: str
    ) -> UserRoleLink | None:
        statement = (
            select(UserRoleLink)
            .where(UserRoleLink.role_code == role_code, UserRoleLink.user_id == user_id)
            .where(UserRoleLink)
        )
        return self.session.exec(statement).first()

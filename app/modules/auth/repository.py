from datetime import datetime, timezone
from sqlmodel import select, update
from app.core.repository import BaseRepository
from app.modules.auth.models import RefreshToken


class RefreshTokenRepository(BaseRepository["RefreshToken"]):
    def __init__(self, session) -> None:
        super().__init__(session, RefreshToken)

    def get_valid_by_hash(self, token_hash: str) -> RefreshToken | None:
        now = datetime.now(timezone.utc)
        statement = (
            select(RefreshToken)
            .where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.is_revoked == False,
                RefreshToken.expires_at > now,
            )
        )
        return self.session.exec(statement).first()

    def revoke_all_for_user(self, user_id: int) -> None:
        now = datetime.now(timezone.utc)
        statement = (
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.is_revoked == False,
                RefreshToken.expires_at > now,
            )
            .values(is_revoked=True)
        )
        self.session.exec(statement)
        self.session.flush()

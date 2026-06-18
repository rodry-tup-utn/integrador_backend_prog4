from datetime import datetime, timedelta, timezone
from app.core.config import settings
from app.core.exceptions import ResourceNotFoundError, AuthenticationError
from app.modules.user.services.user_service import UserService
from app.modules.auth.schemas import JWTPayload
from app.modules.auth.unit_of_work import AuthUnitOfWork
from app.modules.auth.models import RefreshToken
from app.core.security import (
    verify_password,
    create_access_token,
    generate_refresh_token,
    hash_token,
)


class AuthService:
    def __init__(self, session) -> None:
        self._session = session
        self._user_service = UserService(session)

    def login(self, email: str, password: str) -> tuple[str, int]:
        try:
            user_credentials = self._user_service.get_auth_credentials(email)
        except ResourceNotFoundError:
            raise AuthenticationError(
                message="Email o contraseña incorrectos",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not verify_password(password, user_credentials.hashed_pass):
            raise AuthenticationError(
                message="Email o contraseña incorrectos",
                headers={"WWW-Authenticate": "Bearer"},
            )

        payload = JWTPayload(
            sub=str(user_credentials.id),
            role=user_credentials.roles,
            name=user_credentials.name,
        )

        token = create_access_token(payload)

        return token, user_credentials.id

    def create_refresh_token(self, user_id: int) -> str:
        raw_token = generate_refresh_token()
        token_hash = hash_token(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.refresh_token_expire_days
        )
        refresh = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        with AuthUnitOfWork(self._session) as uow:
            uow.refresh_tokens.add(refresh)
        return raw_token

    def validate_refresh_token(self, raw_token: str) -> int:
        token_hash = hash_token(raw_token)
        with AuthUnitOfWork(self._session) as uow:
            refresh = uow.refresh_tokens.get_valid_by_hash(token_hash)
            if not refresh:
                raise AuthenticationError(
                    message="Refresh token inválido o expirado",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return refresh.user_id

    def revoke_user_refresh_tokens(self, user_id: int) -> None:
        with AuthUnitOfWork(self._session) as uow:
            uow.refresh_tokens.revoke_all_for_user(user_id)

    def refresh_tokens(self, raw_token: str) -> tuple[str, str]:
        user_id = self.validate_refresh_token(raw_token)
        self.revoke_user_refresh_tokens(user_id)

        user_data = self._user_service.get_session_data(user_id)
        payload = JWTPayload(
            sub=str(user_data.id),
            role=user_data.roles,
            name=user_data.name,
        )
        new_access_token = create_access_token(payload)
        new_refresh_token = self.create_refresh_token(user_id)

        return new_access_token, new_refresh_token

from app.core.exceptions import ResourceNotFoundError, AuthenticationError
from app.modules.user.services.user_service import UserService
from app.modules.auth.schemas import JWTPayload
from app.core.security import verify_password, create_access_token


class AuthService:
    def __init__(self, session) -> None:
        self._user_service = UserService(session)

    def login(self, email: str, password: str) -> str:
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

        return token

from fastapi import HTTPException, status
from app.modules.user.service import UserService
from app.modules.auth.schemas import Token, JWTPayload
from app.core.security import verify_password, create_access_token


class AuthService:
    def __init__(self, session) -> None:
        self._user_service = UserService(session)

    def login(self, email: str, password: str) -> Token:
        try:
            user_credentials = self._user_service.get_auth_credentials(email)
        except HTTPException:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email o contraseña incorrectos",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not verify_password(password, user_credentials.hashed_pass):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email o contraseña incorrectos",
                headers={"WWW-Authenticate": "Bearer"},
            )

        payload = JWTPayload(
            sub=str(user_credentials.id),
            role=user_credentials.role,
            email=user_credentials.email,
        )

        access_token = create_access_token(payload)

        return Token(access_token=access_token)

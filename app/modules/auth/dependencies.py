from fastapi import Depends, Request
from app.core.exceptions import (
    AuthorizationError,
    AuthenticationError,
    ResourceNotFoundError,
)
from fastapi.security import OAuth2PasswordBearer
import jwt
from sqlmodel import Session
from app.core.config import settings
from app.core.database import get_session
from app.modules.user.services.user_service import UserService
from typing import Annotated
from app.modules.user.schemas import UserDetailRead, TokenPayloadData


class OAuth2PasswordBearerWithCookie(OAuth2PasswordBearer):
    async def __call__(self, request: Request) -> str | None:
        token = request.cookies.get("access_token")
        if not token:
            if self.auto_error:
                raise AuthenticationError(
                    message="Usuario no autenticado",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                return None
        return token


oauth2_scheme = OAuth2PasswordBearerWithCookie(tokenUrl="auth/login")


def get_user_service(session: Session = Depends(get_session)) -> UserService:
    return UserService(session)


def get_token_payload(
    token: str = Depends(oauth2_scheme),
) -> TokenPayloadData:

    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        user_id = payload.get("sub")
        role = payload.get("role")
        name = payload.get("name")

        if user_id is None or role is None or name is None:
            raise AuthenticationError(
                message="Usuario no autenticado", headers={"WWW-Authenticate": "Bearer"}
            )

        return TokenPayloadData(id=int(user_id), roles=role, name=name)
    except jwt.PyJWTError:
        raise AuthenticationError(
            "Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    token_data: TokenPayloadData = Depends(get_token_payload),
    svc: UserService = Depends(get_user_service),
) -> UserDetailRead:
    try:
        user = svc.get_user_with_active_roles(token_data.id)
        return user
    except ResourceNotFoundError:
        raise AuthenticationError(
            "Usuario no autenticado", headers={"WWW-Authenticate": "Bearer"}
        )


def require_role(allowed_roles: list[str]):
    async def role_checker(
        current_user: Annotated[UserDetailRead, Depends(get_current_user)],
    ) -> UserDetailRead:

        user_roles = [link.role_user.code for link in current_user.roles]
        for code in user_roles:
            if code in allowed_roles:
                return current_user

        raise AuthorizationError(
            message=(
                f"Permisos insuficientes. Tus roles son {user_roles}. "
                f"Se requiere uno de: {allowed_roles}"
            ),
        )

    return role_checker  # Retorna la dependencia configurada


def get_refresh_token_from_cookie(request: Request) -> str:
    token = request.cookies.get("refresh_token")
    if not token:
        raise AuthenticationError(
            message="Refresh token no encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token

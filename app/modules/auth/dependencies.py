from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
import jwt
from sqlmodel import Session
from app.core.config import settings
from app.core.database import get_session
from app.modules.user.service import UserService
from app.modules.auth.schemas import UserTokenData
from typing import Annotated
from app.modules.user.models import User
from app.modules.user.schemas import UserPrivate


class OAuth2PasswordBearerWithCookie(OAuth2PasswordBearer):
    async def __call__(self, request: Request) -> str | None:
        token = request.cookies.get("access_token")
        if not token:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="No autenticado",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                return None
        return token


oauth2_scheme = OAuth2PasswordBearerWithCookie(tokenUrl="auth/login")

forbidden_exception = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="No tienes permisos para ejecutar esta operacion",
    headers={"WWW-Authenticate": "Bearer"},
)
unauthorized_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="No se pudieron validar las credenciales",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_user_service(session: Session = Depends(get_session)) -> UserService:
    return UserService(session)


def get_token_payload(
    token: str = Depends(oauth2_scheme),
) -> UserTokenData:

    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        user_id = payload.get("sub")
        role = payload.get("role")
        name = payload.get("name")

        if user_id is None or role is None or name is None:
            raise unauthorized_exception

        return UserTokenData(id=int(user_id), role=role, name=name)
    except jwt.PyJWTError:
        raise unauthorized_exception


def get_current_user(
    token_data: UserTokenData = Depends(get_token_payload),
    svc: UserService = Depends(get_user_service),
):
    try:
        user = svc.get_active_by_id(token_data.id)
        return user
    except HTTPException:
        raise unauthorized_exception


def require_role(allowed_roles: list[str]):
    async def role_checker(
        current_user: Annotated[UserPrivate, Depends(get_current_user)],
    ) -> UserPrivate:

        user_roles = [link.code for link in current_user.roles]
        for code in user_roles:
            if code in allowed_roles:
                return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Permisos insuficientes. Tus roles son {user_roles}. "
                f"Se requiere uno de: {allowed_roles}"
            ),
        )

    return role_checker  # Retorna la dependencia configurada

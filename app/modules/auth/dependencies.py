from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from sqlmodel import Session
from app.core.config import settings
from app.core.database import get_session
import app.modules.user.models as UserModel
from app.modules.user.service import UserService
from app.modules.auth.schemas import UserTokenData
from app.modules.user.schemas import UserPrivate

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

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


def get_current_admin_user(
    current_user: UserTokenData = Depends(get_token_payload),
    svc: UserService = Depends(get_user_service),
) -> UserPrivate:
    try:
        user = svc.get_active_by_id(current_user.id)
        if user.role != UserModel.Role.ADMIN:
            raise forbidden_exception
    except Exception:
        raise forbidden_exception

    return user

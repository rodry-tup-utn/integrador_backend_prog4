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

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="No se pudieron validar las credenciales",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_user_service(session: Session = Depends(get_session)) -> UserService:
    return UserService(session)


def get_token_payload(
    token: str = Depends(oauth2_scheme),
) -> UserTokenData:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        user_id = payload.get("sub")
        role = payload.get("role")
        name = payload.get("name")

        if user_id is None or role is None or name is None:
            raise credentials_exception

        return UserTokenData(id=int(user_id), role=role, name=name)
    except jwt.PyJWTError:
        raise credentials_exception


def get_current_user(
    token_data: UserTokenData = Depends(get_token_payload),
    svc: UserService = Depends(get_user_service),
):
    user = svc.get_active_by_id(token_data.id)
    return user


def get_current_admin_user(
    current_user: UserTokenData = Depends(get_token_payload),
    svc: UserService = Depends(get_user_service),
) -> UserPrivate:
    try:
        user = svc.get_active_by_id(current_user.id)
        if user.role != UserModel.Role.ADMIN:
            raise credentials_exception
    except Exception:
        raise credentials_exception

    return user

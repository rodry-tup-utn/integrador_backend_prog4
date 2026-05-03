from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from sqlmodel import Session
from app.core.config import settings
from app.core.database import get_session
from app.modules.user.models import User, Role
from app.modules.user.schemas import UserPrivate
from app.modules.user.service import UserService
from app.modules.auth.schemas import UserTokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_user_service(session: Session = Depends(get_session)) -> UserService:
    return UserService(session)


def get_current_user_token(
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
        email = payload.get("email")

        if user_id is None or role is None or email is None:
            raise credentials_exception

        return UserTokenData(id=int(user_id), role=role, email=email)
    except jwt.PyJWTError:
        raise credentials_exception


def get_current_admin_user(
    current_user: UserTokenData = Depends(get_current_user_token),
) -> UserTokenData:
    if current_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos suficientes para realizar esta acción",
        )
    result = UserTokenData.model_validate(current_user)
    return result

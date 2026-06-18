from fastapi import APIRouter, Depends, Response
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated
from sqlmodel import Session
from app.core.database import get_session
from app.core.config import settings
from app.modules.auth.service import AuthService
from app.modules.auth.dependencies import (
    get_refresh_token_from_cookie,
    get_current_user,
)
from app.modules.user.schemas import UserDetailRead

router = APIRouter(prefix="/auth", tags=["Autenticación"])


def get_auth_service(session: Session = Depends(get_session)) -> AuthService:
    return AuthService(session)


@router.post("/login")
def login_for_access_token(
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth_service: AuthService = Depends(get_auth_service),
):
    access_token, user_id = auth_service.login(
        email=form_data.username, password=form_data.password
    )
    refresh_token = auth_service.create_refresh_token(user_id)
    is_production = settings.environment == "production"

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=1800,
        samesite="none" if is_production else "lax",
        secure=True,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=settings.refresh_token_expire_days * 86400,
        samesite="none" if is_production else "lax",
        secure=True,
    )
    return {"message": "Login exitoso. Sesión iniciada"}


@router.post("/refresh")
def refresh_access_token(
    response: Response,
    refresh_token: str = Depends(get_refresh_token_from_cookie),
    auth_service: AuthService = Depends(get_auth_service),
):
    new_access_token, new_refresh_token = auth_service.refresh_tokens(refresh_token)
    is_production = settings.environment == "production"

    response.set_cookie(
        key="access_token",
        value=new_access_token,
        httponly=True,
        max_age=1800,
        samesite="none" if is_production else "lax",
        secure=True,
    )
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        max_age=settings.refresh_token_expire_days * 86400,
        samesite="none" if is_production else "lax",
        secure=True,
    )
    return {"message": "Token renovado exitosamente"}


@router.post("/logout")
def logout(
    response: Response,
    current_user: Annotated[UserDetailRead, Depends(get_current_user)],
    auth_service: AuthService = Depends(get_auth_service),
):
    auth_service.revoke_user_refresh_tokens(current_user.id)
    is_production = settings.environment == "production"

    response.delete_cookie(
        key="access_token",
        secure=True,
        httponly=True,
        samesite="none" if is_production else "lax",
    )
    response.delete_cookie(
        key="refresh_token",
        secure=True,
        httponly=True,
        samesite="none" if is_production else "lax",
    )
    return {"message": "Logout exitoso"}

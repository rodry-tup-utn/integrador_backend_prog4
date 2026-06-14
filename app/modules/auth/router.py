from fastapi import APIRouter, Depends, Response
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated
from sqlmodel import Session
from app.core.database import get_session
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["Autenticación"])


def get_auth_service(session: Session = Depends(get_session)) -> AuthService:
    return AuthService(session)


@router.post("/login")
def login_for_access_token(
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Endpoint para iniciar sesión.
    Nota: OAuth2PasswordRequestForm usa el campo 'username' por defecto.
    Aquí tratamos a 'username' como si fuera el 'email'.
    """
    token = auth_service.login(email=form_data.username, password=form_data.password)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=1800,  # 30 minutos, o el valor de expires_in
        samesite="lax",
        secure=False,  # En producción con HTTPS debería ser True
    )
    return {"message": "Login exitoso. Sesión iniciada"}

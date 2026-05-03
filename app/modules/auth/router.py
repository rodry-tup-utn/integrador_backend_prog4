from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated
from sqlmodel import Session
from app.core.database import get_session
from app.modules.auth.service import AuthService
from app.modules.auth.schemas import Token

router = APIRouter(prefix="/auth", tags=["Autenticación"])


def get_auth_service(session: Session = Depends(get_session)) -> AuthService:
    return AuthService(session)


@router.post("/login", response_model=Token)
def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Endpoint para iniciar sesión.
    Nota: OAuth2PasswordRequestForm usa el campo 'username' por defecto.
    Aquí tratamos a 'username' como si fuera el 'email'.
    """
    token = auth_service.login(email=form_data.username, password=form_data.password)
    return token

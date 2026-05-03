from fastapi import APIRouter, Depends, Query, Path, status
from sqlmodel import Session
from app.modules.user.service import UserService
from app.modules.user.schemas import (
    UserBase,
    UserCreate,
    UserUpdate,
    UserPrivate,
    UserList,
)
from typing import Annotated
from app.modules.user.models import Role
from app.core.database import get_session
from app.modules.auth.dependencies import get_current_user_token, get_current_admin_user


def get_user_service(session: Session = Depends(get_session)):
    return UserService(session)


public_router = APIRouter(prefix="/user", tags=["Usuarios - Public"])

admin_router = APIRouter(
    prefix="/admin/user",
    tags=["Usuarios - Admin"],
    dependencies=[Depends(get_current_admin_user)],
)

user_router = APIRouter(
    prefix="/profile",
    tags=["Usuarios - Sesion"],
    dependencies=[Depends(get_current_user_token)],
)


public_router = APIRouter(prefix="/user", tags=["Usuarios - Public"])

admin_router = APIRouter(
    prefix="/admin/user",
    tags=["Usuarios - Admin"],
    dependencies=[Depends(get_current_admin_user)],
)

user_router = APIRouter(
    prefix="/profile",
    tags=["Usuarios - Sesion"],
    dependencies=[Depends(get_current_user_token)],
)

# --- USER ROUTES (SESIÓN) ---


@user_router.get("/me", response_model=UserPrivate)
def get_my_profile(
    user: UserPrivate = Depends(get_current_user_token),
    svc: UserService = Depends(get_user_service),
):
    return svc.get_active_by_id(user.id)


@user_router.patch("/update", response_model=UserPrivate)
def update_profile(
    data: UserUpdate,
    user: UserPrivate = Depends(get_current_user_token),
    svc: UserService = Depends(get_user_service),
):
    return svc.update_profile(user.id, data)


# --- PUBLIC ROUTES ---


@public_router.post("/", response_model=UserBase, status_code=status.HTTP_201_CREATED)
def create_user(data: UserCreate, svc: UserService = Depends(get_user_service)):
    return svc.create(data)


# --- ADMIN ROUTES ---


@admin_router.get("/", response_model=UserList)
def get_all_users(
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1)] = 20,
    svc: UserService = Depends(get_user_service),
):
    return svc.get_all(offset, limit)


@admin_router.get("/{id}", response_model=UserPrivate)
def get_user_by_admin(
    id: Annotated[int, Path(ge=1)], svc: UserService = Depends(get_user_service)
):
    return svc.get_by_id(id)


@admin_router.patch("/{id}/role", response_model=UserPrivate)
def update_user_role(
    id: Annotated[int, Path(ge=1)],
    role: Role,
    svc: UserService = Depends(get_user_service),
):
    return svc.update_role(id, role)


@admin_router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    id: Annotated[int, Path(ge=1)],
    svc: UserService = Depends(get_user_service),
    admin_user: UserPrivate = Depends(get_current_admin_user),
):
    return svc.soft_delete(id, admin_user.id)


@admin_router.patch("/restore/{id}", response_model=UserBase)
def restore_user(
    id: Annotated[int, Path(ge=1)], svc: UserService = Depends(get_user_service)
):
    return svc.restore(id)

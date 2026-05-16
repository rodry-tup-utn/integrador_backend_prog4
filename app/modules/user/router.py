from fastapi import APIRouter, Depends, Query, Path, status, Body
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
from app.core.database import get_session
from app.modules.auth.dependencies import get_token_payload, require_role


def get_user_service(session: Session = Depends(get_session)):
    return UserService(session)


public_router = APIRouter(prefix="/user", tags=["Usuarios - Public"])

admin_router = APIRouter(
    prefix="/admin/user",
    tags=["Usuarios - Admin"],
    dependencies=[Depends(require_role(["ADMIN"]))],
)

user_router = APIRouter(
    prefix="/profile",
    tags=["Usuarios - Sesion"],
    dependencies=[Depends(get_token_payload)],
)


public_router = APIRouter(prefix="/user", tags=["Usuarios - Public"])

admin_router = APIRouter(
    prefix="/admin/user",
    tags=["Usuarios - Admin"],
    dependencies=[Depends(require_role(["ADMIN"]))],
)

user_router = APIRouter(
    prefix="/profile",
    tags=["Usuarios - Sesion"],
    dependencies=[Depends(get_token_payload)],
)

# --- USER ROUTES (SESIÓN) ---


@user_router.get("/me", response_model=UserPrivate)
def get_my_profile(
    user: UserPrivate = Depends(get_token_payload),
    svc: UserService = Depends(get_user_service),
):
    return svc.get_active_by_id(user.id)


@user_router.patch("/update", response_model=UserPrivate)
def update_profile(
    data: UserUpdate,
    user: UserPrivate = Depends(get_token_payload),
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


@admin_router.post("/{id}/role/{role_code}")
def assign_user_role(
    id: Annotated[int, Path(ge=1)],
    role_code: Annotated[str, Path(max_length=8)],
    svc: UserService = Depends(get_user_service),
    admin_user: UserPrivate = Depends(require_role(["ADMIN"])),
):
    svc.asign_role(id, role_code, admin_user.id)
    return {"message": "Rol asignado correctamente"}


@admin_router.delete("/{id}/role/{role_code}")
def revoke_user_role(
    id: Annotated[int, Path(ge=1)],
    role_code: Annotated[str, Path()],
    svc: UserService = Depends(get_user_service),
):
    svc.revoke_role(id, role_code)
    return {"message": "Rol revocado correctamente"}


@admin_router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    id: Annotated[int, Path(ge=1)],
    svc: UserService = Depends(get_user_service),
    admin_user: UserPrivate = Depends(require_role(["ADMIN"])),
):
    return svc.soft_delete(id, admin_user.id)


@admin_router.patch("/restore/{id}", response_model=UserBase)
def restore_user(
    id: Annotated[int, Path(ge=1)], svc: UserService = Depends(get_user_service)
):
    return svc.restore(id)

from fastapi import APIRouter, Depends, Query, Path, status
from sqlmodel import Session
from app.modules.user.services.user_service import UserService
from app.modules.user.services.adress_service import DeliveryAdressService
from app.modules.user.schemas import (
    UserBase,
    UserCreate,
    UserUpdate,
    UserPrivate,
    UserList,
    UserDetail,
    UserProfile,
    DeliveryAdressCreate,
    DeliveryAdressUpdate,
    DeliveryAdressRead,
)
from app.modules.auth.schemas import UserTokenData
from typing import Annotated
from app.core.database import get_session
from app.modules.auth.dependencies import (
    require_role,
    get_current_user,
    get_token_payload,
)


def get_user_service(session: Session = Depends(get_session)):
    return UserService(session)


def get_address_service(session: Session = Depends(get_session)):
    return DeliveryAdressService(session)


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


# trabaja con get token payload para evitar llamada a db en lectura
@user_router.get("/me", response_model=UserProfile)
def get_my_profile(
    user_data: UserTokenData = Depends(get_token_payload),
    svc: UserService = Depends(get_user_service),
):
    return svc.get_user_profile(user_data.id)


@user_router.patch("/update", response_model=UserPrivate)
def update_profile(
    data: UserUpdate,
    user_data: UserTokenData = Depends(get_token_payload),
    svc: UserService = Depends(get_user_service),
):
    return svc.update_profile(user_data.id, data)


@user_router.get("/address", response_model=list[DeliveryAdressRead])
def list_my_addresses(
    user: UserDetail = Depends(get_current_user),
    svc: DeliveryAdressService = Depends(get_address_service),
):
    return svc.get_active_by_user_id(user.id)


@user_router.post(
    "/address", response_model=DeliveryAdressRead, status_code=status.HTTP_201_CREATED
)
def create_address(
    data: DeliveryAdressCreate,
    user: UserDetail = Depends(get_current_user),
    svc: DeliveryAdressService = Depends(get_address_service),
):
    return svc.create(user.id, data)


@user_router.patch("/address/{id}", response_model=DeliveryAdressRead)
def update_address(
    id: Annotated[int, Path(ge=1)],
    data: DeliveryAdressUpdate,
    user: UserDetail = Depends(get_current_user),
    svc: DeliveryAdressService = Depends(get_address_service),
):
    return svc.update(id, data, user.id)


@user_router.delete("/address/{id}")
def delete_address(
    id: Annotated[int, Path(ge=1)],
    user: UserDetail = Depends(get_current_user),
    svc: DeliveryAdressService = Depends(get_address_service),
):
    svc.soft_delete(id, user.id)
    return {"message": "Domicilio eliminado correctamente"}


@user_router.patch("/address/{id}/restore", response_model=DeliveryAdressRead)
def restore_address(
    id: Annotated[int, Path(ge=1)],
    user: UserDetail = Depends(get_current_user),
    svc: DeliveryAdressService = Depends(get_address_service),
):
    return svc.restore(id, user.id)


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


@admin_router.get("/{id}", response_model=UserDetail)
def get_user_by_admin(
    id: Annotated[int, Path(ge=1)], svc: UserService = Depends(get_user_service)
):
    return svc.get_by_id(id)


@admin_router.post("/{id}/role/{role_code}")
def assign_user_role(
    id: Annotated[int, Path(ge=1)],
    role_code: Annotated[str, Path(max_length=8)],
    svc: UserService = Depends(get_user_service),
    admin_user: UserDetail = Depends(require_role(["ADMIN"])),
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
    admin_user: UserDetail = Depends(require_role(["ADMIN"])),
):
    return svc.soft_delete(id, admin_user.id)


@admin_router.patch("/restore/{id}", response_model=UserBase)
def restore_user(
    id: Annotated[int, Path(ge=1)], svc: UserService = Depends(get_user_service)
):
    return svc.restore(id)

from fastapi import APIRouter, Depends, Path, status
from sqlmodel import Session
from typing import Annotated
from app.core.database import get_session
from app.modules.order.services.order_service import OrderService
from app.modules.order.schemas import (
    OrderCreate,
    OrderDetailPublic,
    OrderList,
    OrderFilters,
    OrderClientFilters,
    OrderStateChange,
    OrderCancelByStaff,
    OrderAdminList,
)
from app.modules.auth.dependencies import require_role, get_token_payload
from app.modules.user.schemas import TokenPayloadData


def get_order_service(session: Session = Depends(get_session)) -> OrderService:
    return OrderService(session)


user_router = APIRouter(
    prefix="/order",
    tags=["Orders - User"],
    dependencies=[Depends(get_token_payload)],
)

admin_router = APIRouter(
    prefix="/admin/order",
    tags=["Orders - Admin"],
    dependencies=[Depends(require_role(["ADMIN"]))],
)

orders_router = APIRouter(
    prefix="/orders/order",
    tags=["Orders - Management"],
    dependencies=[Depends(require_role(["ORDERS", "ADMIN"]))],
)


@user_router.post(
    "/", response_model=OrderDetailPublic, status_code=status.HTTP_201_CREATED
)
async def create_order(
    data: OrderCreate,
    user_data: Annotated[TokenPayloadData, Depends(get_token_payload)],
    svc: Annotated[OrderService, Depends(get_order_service)],
):
    return await svc.create(data, user_data.id)


@user_router.get("/", response_model=OrderList)
def list_my_orders(
    user_data: Annotated[TokenPayloadData, Depends(get_token_payload)],
    svc: Annotated[OrderService, Depends(get_order_service)],
    filters: OrderClientFilters = Depends(),
):
    return svc.list_by_user(user_data.id, filters)


@user_router.get("/{id}", response_model=OrderDetailPublic)
def get_my_order(
    id: Annotated[int, Path(ge=1)],
    user_data: Annotated[TokenPayloadData, Depends(get_token_payload)],
    svc: Annotated[OrderService, Depends(get_order_service)],
):
    return svc.get_by_id(id, user_data.id)


@user_router.post("/{id}/cancel", response_model=OrderDetailPublic)
async def cancel_my_order(
    id: Annotated[int, Path(ge=1)],
    user_data: Annotated[TokenPayloadData, Depends(get_token_payload)],
    svc: Annotated[OrderService, Depends(get_order_service)],
):
    return await svc.cancel(id, user_data.id)


@admin_router.delete("/{id}/delete", status_code=status.HTTP_204_NO_CONTENT)
def soft_delete(
    id: Annotated[int, Path(ge=1)],
    svc: Annotated[OrderService, Depends(get_order_service)],
):
    svc.soft_delete(id)


@orders_router.get("/", response_model=OrderAdminList)
def list_all_orders_staff(
    svc: Annotated[OrderService, Depends(get_order_service)],
    filters: OrderFilters = Depends(),
):
    return svc.list_all_admin(filters)


@orders_router.get("/{id}", response_model=OrderDetailPublic)
def get_order_by_staff(
    id: Annotated[int, Path(ge=1)],
    svc: Annotated[OrderService, Depends(get_order_service)],
):
    return svc.get_by_id_admin(id)


@orders_router.patch("/{id}/state", response_model=OrderDetailPublic)
async def change_order_state(
    id: Annotated[int, Path(ge=1)],
    data: OrderStateChange,
    svc: Annotated[OrderService, Depends(get_order_service)],
):
    return await svc.change_state(id, data.state_code, data.reason)


@orders_router.post("/{id}/cancel", response_model=OrderDetailPublic)
async def cancel_order_by_staff(
    id: Annotated[int, Path(ge=1)],
    data: OrderCancelByStaff,
    svc: Annotated[OrderService, Depends(get_order_service)],
):
    return await svc.cancel_by_staff(id, data.reason)

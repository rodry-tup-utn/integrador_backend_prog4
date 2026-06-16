from fastapi import APIRouter, Depends, Path, Request, status, Header
from sqlmodel import Session
from typing import Annotated

from app.modules.payments.service import PaymentService
from app.modules.payments.schemas import PaymentPublic, CheckoutPreferenceResponse

from app.core.database import get_session
from app.modules.auth.dependencies import require_role


def get_payment_service(session: Session = Depends(get_session)) -> PaymentService:
    return PaymentService(session)


router = APIRouter(prefix="/payment", tags=["Public - Pagos"])

admin_router = APIRouter(
    prefix="/admin/payment",
    tags=["Admin - Pagos"],
    dependencies=[Depends(require_role(["ADMIN"]))],
)


@router.post(
    "/checkout/{order_id}",
    response_model=CheckoutPreferenceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_checkout(
    order_id: Annotated[int, Path(ge=1)],
    svc: PaymentService = Depends(get_payment_service),
):
    return svc.create_preference(order_id)


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def mp_webhook(
    request: Request,
    svc: PaymentService = Depends(get_payment_service),
    x_signature: Annotated[str | None, Header(alias="x-signature")] = None,
    x_request_id: Annotated[str | None, Header(alias="x-request-id")] = None,
):
    body: dict = {}
    try:
        body = await request.json()
    except Exception:
        body = {}

    return await svc.process_notification_webook(
        body=body,
        query_params=dict(request.query_params),
        x_signature=x_signature,
        x_request_id=x_request_id,
    )


@admin_router.get("/order/{order_id}", response_model=list[PaymentPublic])
def get_by_order_id(
    order_id: Annotated[int, Path(ge=1)],
    svc: PaymentService = Depends(get_payment_service),
):
    return svc.get_by_order_id(order_id)

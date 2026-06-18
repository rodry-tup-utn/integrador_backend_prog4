from fastapi import HTTPException, status
from sqlmodel import Session
import uuid
import logging

from app.modules.payments.models import Payment
from app.modules.payments.schemas import CheckoutPreferenceResponse, PaymentPublic

from app.modules.payments.unit_of_work import PaymentUnitOfWork
from app.modules.order.models import Order
from app.core.mercadopago.utils import get_mp_sdk, verify_mp_signature
from app.core.mercadopago.config import mp_settings
from app.modules.websocket.manager import manager
from mercadopago.config import RequestOptions

logger = logging.getLogger(__name__)

ORDER_STATE_PENDING = "PENDING"
ORDER_STATE_CONFIRMED = "CONFIRMED"
MP_STATUS_APPROVED = "approved"
WS_EVENT_PAYMENT_APPROVED = "payment_approved"
WS_ROLES_TO_NOTIFY = ["ORDERS", "ADMIN"]


def not_found_exception(name: str, id: int | str):
    raise HTTPException(
        status.HTTP_404_NOT_FOUND, f"{name.capitalize()} con id {id} no encontrado"
    )


class PaymentService:
    def __init__(self, session: Session) -> None:
        self._session = session

    # helper para buscar una orden - pedido por id
    def _get_order_or_404(self, uow: PaymentUnitOfWork, order_id: int) -> Order:
        order = uow.ordersRepo.get_by_id(order_id)

        if not order:
            raise not_found_exception("Orden", order_id)
        return order

    # helper para buscar un pago por su id
    def _get_payment_or_404(self, uow: PaymentUnitOfWork, payment_id: int) -> Payment:
        payment = uow.paymentsRepo.get_by_id(payment_id)

        if not payment:
            raise not_found_exception("Pago", payment_id)
        return payment

    # helper para verificar el estado de una orden antes de crear el pago
    def _assert_order_status(self, order: Order) -> None:
        if order.state_code != ORDER_STATE_PENDING:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="La orden no se encuentra en un estado que permita generar un pago",
            )

    # Helper para armar la preference_data del checkout de MP
    def _build_preference_payload(self, order: Order, payment: Payment) -> dict:
        total = order.subtotal - order.discount + order.shipping_cost

        return {
            "items": [
                {
                    "title": f"Orden #{order.id}",
                    "quantity": 1,
                    "unit_price": float(total),
                    "currency_id": "ARS",
                },
            ],
            "external_reference": payment.external_reference,
            "back_urls": {
                "success": f"{mp_settings.FRONTEND_SUCCESS_URL}?order_id={order.id}",
                "failure": f"{mp_settings.FRONTEND_FAILURE_URL}?order_id={order.id}",
                "pending": f"{mp_settings.FRONTEND_PENDING_URL}?order_id={order.id}",
            },
            # "auto_return": "approved",
            "notification_url": mp_settings.BACKEND_NOTIFICATION_URL,
        }

    # Helper para validar la firma de la notificación de MercadoPago
    def _validate_webhook_request(
        self,
        body: dict,
        query_params: dict,
        x_signature: str | None,
        x_request_id: str | None,
    ) -> tuple[str | None, str | None]:
        notification_type = body.get("type") or query_params.get("type")

        data_id_raw = (
            (body.get("data") or {}).get("id")
            or query_params.get("data_id")
            or query_params.get("id")
        )

        data_id = str(data_id_raw) if data_id_raw is not None else None

        signature_data_id = data_id.lower() if data_id is not None else None

        if not verify_mp_signature(x_signature, x_request_id, signature_data_id):
            # raise HTTPException(
            #     status.HTTP_401_UNAUTHORIZED, detail="Firma de notificación inválida"
            # )
            logger.warning(
                "Firma de notificación inválida para data_id=%s (no se bloquea)",
                data_id,
            )

        return notification_type, data_id

    async def _emit_ws_payment_event(self, order_id: int) -> None:
        data = {"order_id": order_id}
        await manager.broadcast_to_order(order_id, WS_EVENT_PAYMENT_APPROVED, data)
        await manager.broadcast_to_roles(
            WS_ROLES_TO_NOTIFY, WS_EVENT_PAYMENT_APPROVED, data
        )
        logger.info(
            f"WS emitido: {WS_EVENT_PAYMENT_APPROVED} | pedido={order_id} | "
            f"rooms_activas={manager.get_rooms_info()}"
        )

    # método que crea la preferencia de pago para el checkout
    def create_preference(self, order_id: int) -> CheckoutPreferenceResponse:
        with PaymentUnitOfWork(self._session) as uow:
            order = self._get_order_or_404(uow, order_id)
            self._assert_order_status(order)

            total = order.subtotal - order.discount + order.shipping_cost

            if total <= 0:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    detail="El total de la orden debe ser mayor a cero para iniciar el pago",
                )

            payment = uow.paymentsRepo.get_pending_by_order_id(order_id)

            if payment is not None:
                payment.transaction_amount = total
                uow.paymentsRepo.add(payment)
            else:
                payment = Payment(
                    order_id=order.id,  # type: ignore
                    external_reference=f"order-{order.id}",
                    idempotency_key=str(uuid.uuid4()),
                    transaction_amount=total,
                    mp_status="pending",
                )
                uow.paymentsRepo.add(payment)

            preference_payload = self._build_preference_payload(order, payment)

            sdk = get_mp_sdk()
            request_options = RequestOptions(
                custom_headers={"x-idempotency-key": payment.idempotency_key}
            )
            try:
                response = sdk.preference().create(preference_payload, request_options)
            except Exception:
                logger.exception(
                    "Error al crear la preferencia de Mercado Pago para order_id=%s",
                    order_id,
                )
                raise HTTPException(
                    status.HTTP_502_BAD_GATEWAY,
                    detail="No se pudo iniciar el pago con Mercado Pago",
                )

            if response.get("status") not in (200, 201):
                logger.error(
                    "Mercado Pago devolvió un error al crear la preferencia: %s",
                    response,
                )
                raise HTTPException(
                    status.HTTP_502_BAD_GATEWAY,
                    detail="No se pudo iniciar el pago con Mercado Pago",
                )

            preference = response["response"]

            result = CheckoutPreferenceResponse(
                payment_id=payment.id,  # type: ignore
                preference_id=preference["id"],
                init_point=preference["init_point"],
                sandbox_init_point=preference["sandbox_init_point"],
            )

        return result

    # Obtiene todos los intentos de pago relacionados con un pedido por el id del pedido
    def get_by_order_id(self, order_id: int) -> list[PaymentPublic]:
        with PaymentUnitOfWork(self._session) as uow:
            self._get_order_or_404(uow, order_id)
            payments = uow.paymentsRepo.get_payments_by_order_id(order_id)
            return [PaymentPublic.model_validate(payment) for payment in payments]

    # Método para confirmación de estado de pago de Mercado Pago y cambio del estado de la orden
    async def process_notification_webook(
        self,
        body: dict,
        query_params: dict,
        x_signature: str | None,
        x_request_id: str | None,
    ) -> dict:
        notification_type, data_id = self._validate_webhook_request(
            body, query_params, x_signature, x_request_id
        )

        if notification_type != "payment" or not data_id:
            return {"status": "ignored"}

        mp_payment_id = int(data_id)
        sdk = get_mp_sdk()

        try:
            response = sdk.payment().get(mp_payment_id)
        except Exception:
            logger.exception(
                "Error al consultar el pago %s en Mercado Pago", mp_payment_id
            )
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                detail="No se pudo consultar el pago en Mercado Pago",
            )

        if response.get("status") != 200:
            logger.error(
                "Mercado Pago devolvió un error al consultar el pago %s: %s",
                mp_payment_id,
                response,
            )
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                detail="No se pudo consultar el pago en Mercado Pago",
            )

        mp_payment = response["response"]

        external_reference = mp_payment.get("external_reference")
        mp_status = mp_payment.get("status")
        mp_status_detail = mp_payment.get("status_detail")
        payment_method_id = mp_payment.get("payment_method_id")

        if not external_reference:
            logger.warning(
                "Notificación de pago %s sin external_reference, se ignora",
                mp_payment_id,
            )
            return {"status": "ignored"}

        with PaymentUnitOfWork(self._session) as uow:
            payment = uow.paymentsRepo.get_by_external_reference(external_reference)

            if payment is None:
                logger.warning(
                    "No se encontró Payment con external_reference=%s para mp_payment_id=%s",
                    external_reference,
                    mp_payment_id,
                )
                return {"status": "ignored"}

            payment.mp_payment_id = mp_payment_id
            payment.mp_status = mp_status
            payment.mp_status_detail = mp_status_detail
            payment.payment_method_id = payment_method_id

            uow.paymentsRepo.add(payment)

            if mp_status == MP_STATUS_APPROVED:
                order = uow.ordersRepo.get_by_id(payment.order_id)
                if order and order.state_code == ORDER_STATE_PENDING:
                    uow.ordersRepo.update_state(order, ORDER_STATE_CONFIRMED)
                    await self._emit_ws_payment_event(payment.order_id)

        return {"status": "ok"}

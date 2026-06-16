from datetime import datetime
from decimal import Decimal

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.modules.order.models import Order, PaymentMethod, StateOrder
from app.modules.order_item.models import OrderItem
from app.modules.product.models import Product
from app.modules.user.models import User

APPROVED_STATES = ("CONFIRMED", "IN_PREP", "DELIVERED")


class EstadisticasRepository:

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_resumen_kpis(self) -> tuple:
        total_ordenes = self.session.exec(
            select(func.count())
            .select_from(Order)
            .where(col(Order.deleted_at).is_(None))
        ).one()

        total_ingresos = self.session.exec(
            select(func.coalesce(func.sum(Order.subtotal), 0))
            .where(col(Order.deleted_at).is_(None))
            .where(col(Order.state_code).in_(APPROVED_STATES))
        ).one()
        total_ingresos = Decimal(str(total_ingresos))

        total_approved = self.session.exec(
            select(func.count())
            .select_from(Order)
            .where(col(Order.deleted_at).is_(None))
            .where(col(Order.state_code).in_(APPROVED_STATES))
        ).one()
        promedio = (
            (total_ingresos / Decimal(str(total_approved)))
            if total_approved > 0
            else None
        )

        total_usuarios = self.session.exec(select(func.count()).select_from(User)).one()

        rows = self.session.exec(
            select(Order.state_code, func.count().label("cnt"))
            .where(col(Order.deleted_at).is_(None))
            .group_by(Order.state_code)
        ).all()
        ordenes_por_estado = {row[0]: row[1] for row in rows}

        return (
            total_ordenes,
            total_ingresos,
            promedio,
            total_usuarios,
            ordenes_por_estado,
        )

    def get_ventas_periodo_data(
        self, desde: datetime | None, hasta: datetime | None
    ) -> list[Order]:
        statement = (
            select(Order)
            .where(col(Order.deleted_at).is_(None))
            .where(col(Order.state_code).in_(APPROVED_STATES))
        )
        if desde:
            statement = statement.where(Order.created_at >= desde)
        if hasta:
            statement = statement.where(Order.created_at <= hasta)
        return self.session.exec(statement.order_by(Order.created_at)).all()

    def get_productos_top(self, limit: int) -> list:
        rows = self.session.exec(
            select(
                OrderItem.product_id,
                Product.name,
                func.coalesce(func.sum(OrderItem.quantity), 0).label("cantidad"),
                func.coalesce(func.sum(OrderItem.subtotal_snap), 0).label("ingresos"),
            )
            .select_from(OrderItem)
            .join(Order, OrderItem.order_id == Order.id)
            .join(Product, OrderItem.product_id == Product.id)
            .where(col(Order.deleted_at).is_(None))
            .where(col(Order.state_code).in_(APPROVED_STATES))
            .group_by(OrderItem.product_id, Product.name)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(limit)
        ).all()
        return [
            {
                "producto_id": r[0],
                "nombre": r[1],
                "cantidad_vendida": r[2],
                "ingresos_totales": Decimal(str(r[3])),
            }
            for r in rows
        ]

    def get_pedidos_por_estado(self) -> list:
        rows = self.session.exec(
            select(
                Order.state_code,
                StateOrder.description,
                func.count().label("cnt"),
            )
            .select_from(Order)
            .join(StateOrder, Order.state_code == StateOrder.code)
            .where(col(Order.deleted_at).is_(None))
            .group_by(Order.state_code, StateOrder.description)
        ).all()
        return [{"estado": r[0], "descripcion": r[1], "cantidad": r[2]} for r in rows]

    def get_ingresos_data(self, desde: datetime | None, hasta: datetime | None) -> list:
        statement = (
            select(
                Order.payment_method_code,
                PaymentMethod.description,
                func.coalesce(func.sum(Order.subtotal), 0).label("total"),
            )
            .select_from(Order)
            .join(PaymentMethod, Order.payment_method_code == PaymentMethod.code)
            .where(col(Order.deleted_at).is_(None))
            .where(col(Order.state_code).in_(APPROVED_STATES))
            .group_by(Order.payment_method_code, PaymentMethod.description)
        )
        if desde:
            statement = statement.where(Order.created_at >= desde)
        if hasta:
            statement = statement.where(Order.created_at <= hasta)
        rows = self.session.exec(statement).all()
        return [
            {
                "forma_pago": r[0],
                "descripcion": r[1],
                "total": Decimal(str(r[2])),
            }
            for r in rows
        ]

from datetime import datetime
from decimal import Decimal

from sqlmodel import Session

from app.modules.estadisticas.repository import EstadisticasRepository
from app.modules.estadisticas.schemas import (
    FormaPagoIngreso,
    IngresosResponse,
    PedidosEstadoItem,
    ProductoTopItem,
    ResumenResponse,
    VentasPeriodoItem,
)


def _period_key(dt: datetime, agrupacion: str) -> str:
    if agrupacion == "year":
        return dt.strftime("%Y")
    if agrupacion == "week":
        return dt.strftime("%Y-W%W")
    if agrupacion == "month":
        return dt.strftime("%Y-%m")
    return dt.strftime("%Y-%m-%d")


class EstadisticasService:

    def __init__(self, session: Session) -> None:
        self.repo = EstadisticasRepository(session)

    def get_resumen(self) -> ResumenResponse:
        (
            total_ordenes,
            total_ingresos,
            promedio,
            total_usuarios,
            ordenes_por_estado,
        ) = self.repo.get_resumen_kpis()
        return ResumenResponse(
            total_ordenes=total_ordenes,
            total_ingresos=total_ingresos,
            promedio_orden=promedio,
            total_usuarios=total_usuarios,
            ordenes_por_estado=ordenes_por_estado,
        )

    def get_ventas(
        self,
        desde: datetime | None,
        hasta: datetime | None,
        agrupacion: str = "day",
    ) -> list[VentasPeriodoItem]:
        orders = self.repo.get_ventas_periodo_data(desde, hasta)
        groups: dict[str, dict] = {}
        for o in orders:
            key = _period_key(o.created_at, agrupacion)
            if key not in groups:
                groups[key] = {"total": Decimal("0.00"), "cantidad": 0}
            groups[key]["total"] += o.subtotal
            groups[key]["cantidad"] += 1
        return [
            VentasPeriodoItem(
                periodo=k,
                total=v["total"],
                cantidad_pedidos=v["cantidad"],
            )
            for k, v in sorted(groups.items())
        ]

    def get_productos_top(self, limit: int = 5) -> list[ProductoTopItem]:
        rows = self.repo.get_productos_top(limit)
        return [ProductoTopItem(**r) for r in rows]

    def get_pedidos_por_estado(self) -> list[PedidosEstadoItem]:
        rows = self.repo.get_pedidos_por_estado()
        return [PedidosEstadoItem(**r) for r in rows]

    def get_ingresos(
        self,
        desde: datetime | None,
        hasta: datetime | None,
    ) -> IngresosResponse:
        rows = self.repo.get_ingresos_data(desde, hasta)
        por_forma_pago = [FormaPagoIngreso(**r) for r in rows]
        total = sum(fp.total for fp in por_forma_pago)
        return IngresosResponse(
            total=total,  # type: ignore
            por_forma_pago=por_forma_pago,
            desde=desde,
            hasta=hasta,
        )

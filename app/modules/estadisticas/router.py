from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.core.database import get_session
from app.modules.auth.dependencies import require_role
from app.modules.estadisticas.schemas import (
    IngresosResponse,
    PedidosEstadoItem,
    ProductoTopItem,
    ResumenResponse,
    VentasPeriodoItem,
)
from app.modules.estadisticas.service import EstadisticasService

router = APIRouter(
    prefix="/admin/estadisticas",
    tags=["Estadísticas"],
    dependencies=[Depends(require_role(["ADMIN"]))],
)


def get_estadisticas_service(
    session: Session = Depends(get_session),
) -> EstadisticasService:
    return EstadisticasService(session)


@router.get("/resumen", response_model=ResumenResponse)
def resumen(
    svc: Annotated[EstadisticasService, Depends(get_estadisticas_service)],
):
    return svc.get_resumen()


@router.get("/ventas", response_model=list[VentasPeriodoItem])
def ventas(
    svc: Annotated[EstadisticasService, Depends(get_estadisticas_service)],
    desde: datetime | None = Query(default=None),
    hasta: datetime | None = Query(default=None),
    agrupacion: str = Query(default="day", pattern="^(day|week|month|year)$"),
):
    return svc.get_ventas(desde, hasta, agrupacion)


@router.get("/productos-top", response_model=list[ProductoTopItem])
def productos_top(
    svc: Annotated[EstadisticasService, Depends(get_estadisticas_service)],
    limit: int = Query(default=5, ge=1, le=100),
):
    return svc.get_productos_top(limit)


@router.get("/pedidos-estado", response_model=list[PedidosEstadoItem])
def pedidos_estado(
    svc: Annotated[EstadisticasService, Depends(get_estadisticas_service)],
):
    return svc.get_pedidos_por_estado()


@router.get("/ingresos", response_model=IngresosResponse)
def ingresos(
    svc: Annotated[EstadisticasService, Depends(get_estadisticas_service)],
    desde: datetime | None = Query(default=None),
    hasta: datetime | None = Query(default=None),
):
    return svc.get_ingresos(desde, hasta)

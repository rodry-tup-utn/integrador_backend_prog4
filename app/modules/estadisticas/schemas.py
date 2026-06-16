from datetime import datetime
from decimal import Decimal

from sqlmodel import SQLModel, Field


class ResumenResponse(SQLModel):
    total_ordenes: int
    total_ingresos: Decimal
    promedio_orden: Decimal | None
    total_usuarios: int
    ordenes_por_estado: dict[str, int]


class VentasPeriodoItem(SQLModel):
    periodo: str = Field(max_length=20)
    total: Decimal
    cantidad_pedidos: int


class ProductoTopItem(SQLModel):
    producto_id: int
    nombre: str = Field(max_length=150)
    cantidad_vendida: int
    ingresos_totales: Decimal


class PedidosEstadoItem(SQLModel):
    estado: str = Field(max_length=20)
    descripcion: str | None
    cantidad: int


class FormaPagoIngreso(SQLModel):
    forma_pago: str = Field(max_length=20)
    descripcion: str | None
    total: Decimal


class IngresosResponse(SQLModel):
    total: Decimal
    por_forma_pago: list[FormaPagoIngreso]
    desde: datetime | None = None
    hasta: datetime | None = None

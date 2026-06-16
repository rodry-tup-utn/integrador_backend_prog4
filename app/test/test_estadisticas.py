"""Tests del módulo de estadísticas."""

from datetime import datetime, timezone
from decimal import Decimal

from sqlmodel import select

from app.modules.user.models import User
from app.core.security import get_password_hash


def _create_user(db_session, email: str = "stats_test@test.com") -> User:
    user = User(
        name="Stats",
        lastname="Test",
        email=email,
        hashed_pass=get_password_hash("TestPass123!"),
    )
    db_session.add(user)
    db_session.flush()
    return user


class TestEstadisticas:

    def test_resumen(
        self, db_session, client, admin_headers, producto_factory, pedido_factory
    ):
        user = _create_user(db_session, "resumen@test.com")
        p1 = producto_factory(name="Resumen A", base_price=Decimal("100"), stock=100)
        p2 = producto_factory(name="Resumen B", base_price=Decimal("200"), stock=100)

        o1 = pedido_factory(usuario_id=user.id, producto_id=p1.id)
        o1.state_code = "CONFIRMED"

        o2 = pedido_factory(usuario_id=user.id, producto_id=p2.id, quantity=2)
        o2.state_code = "DELIVERED"

        o3 = pedido_factory(usuario_id=user.id, producto_id=p1.id)
        o3.state_code = "CANCELLED"

        o4 = pedido_factory(usuario_id=user.id, producto_id=p2.id)

        db_session.flush()

        resp = client.get("/admin/estadisticas/resumen", headers=admin_headers)
        data = resp.json()

        assert resp.status_code == 200
        assert data["total_ordenes"] == 4
        assert float(data["total_ingresos"]) == 500.0
        assert float(data["promedio_orden"]) == 250.0
        assert data["total_usuarios"] >= 1
        assert data["ordenes_por_estado"] == {
            "PENDING": 1,
            "CONFIRMED": 1,
            "DELIVERED": 1,
            "CANCELLED": 1,
        }

    def test_ventas_periodo(
        self, db_session, client, admin_headers, producto_factory, pedido_factory
    ):
        user = _create_user(db_session, "ventas@test.com")
        p = producto_factory(name="Ventas P", base_price=Decimal("100"), stock=100)

        o1 = pedido_factory(usuario_id=user.id, producto_id=p.id)
        o1.state_code = "CONFIRMED"
        o1.created_at = datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc)

        o2 = pedido_factory(usuario_id=user.id, producto_id=p.id)
        o2.state_code = "CONFIRMED"
        o2.created_at = datetime(2026, 1, 20, 10, 0, 0, tzinfo=timezone.utc)

        o3 = pedido_factory(usuario_id=user.id, producto_id=p.id)
        o3.state_code = "DELIVERED"
        o3.created_at = datetime(2026, 2, 10, 10, 0, 0, tzinfo=timezone.utc)

        db_session.flush()

        resp = client.get(
            "/admin/estadisticas/ventas",
            params={
                "desde": "2026-01-01T00:00:00Z",
                "hasta": "2026-12-31T23:59:59Z",
                "agrupacion": "month",
            },
            headers=admin_headers,
        )
        data = resp.json()

        assert resp.status_code == 200
        assert len(data) == 2
        assert data[0]["periodo"] == "2026-01"
        assert data[0]["cantidad_pedidos"] == 2
        assert float(data[0]["total"]) == 200.0
        assert data[1]["periodo"] == "2026-02"
        assert data[1]["cantidad_pedidos"] == 1
        assert float(data[1]["total"]) == 100.0

    def test_ventas_periodo_sin_fechas(
        self, db_session, client, admin_headers, producto_factory, pedido_factory
    ):
        user = _create_user(db_session, "ventas2@test.com")
        p = producto_factory(name="Ventas Q", base_price=Decimal("100"), stock=100)

        o1 = pedido_factory(usuario_id=user.id, producto_id=p.id)
        o1.state_code = "CONFIRMED"

        o2 = pedido_factory(usuario_id=user.id, producto_id=p.id, quantity=2)
        o2.state_code = "DELIVERED"

        db_session.flush()

        resp = client.get(
            "/admin/estadisticas/ventas",
            params={"agrupacion": "day"},
            headers=admin_headers,
        )
        data = resp.json()

        assert resp.status_code == 200
        assert len(data) >= 1
        assert sum(item["cantidad_pedidos"] for item in data) == 2

    def test_productos_top(
        self, db_session, client, admin_headers, producto_factory, pedido_factory
    ):
        user = _create_user(db_session, "top@test.com")
        p_a = producto_factory(base_price=Decimal("100"), name="Producto A")
        p_b = producto_factory(base_price=Decimal("200"), name="Producto B")
        p_c = producto_factory(base_price=Decimal("50"), name="Producto C")

        for _ in range(5):
            o = pedido_factory(usuario_id=user.id, producto_id=p_a.id)
            o.state_code = "CONFIRMED"

        for _ in range(3):
            o = pedido_factory(usuario_id=user.id, producto_id=p_b.id)
            o.state_code = "CONFIRMED"

        o = pedido_factory(usuario_id=user.id, producto_id=p_c.id)
        o.state_code = "CONFIRMED"

        db_session.flush()

        resp = client.get(
            "/admin/estadisticas/productos-top",
            params={"limit": 2},
            headers=admin_headers,
        )
        data = resp.json()

        assert resp.status_code == 200
        assert len(data) == 2
        assert data[0]["nombre"] == "Producto A"
        assert data[0]["cantidad_vendida"] == 5
        assert data[1]["nombre"] == "Producto B"
        assert data[1]["cantidad_vendida"] == 3

    def test_pedidos_por_estado(
        self, db_session, client, admin_headers, producto_factory, pedido_factory
    ):
        user = _create_user(db_session, "estados@test.com")
        p = producto_factory(name="Estados P", base_price=Decimal("100"), stock=100)

        for state in ["PENDING", "CONFIRMED", "IN_PREP", "DELIVERED", "CANCELLED"]:
            o = pedido_factory(usuario_id=user.id, producto_id=p.id)
            o.state_code = state

        db_session.flush()

        resp = client.get(
            "/admin/estadisticas/pedidos-estado", headers=admin_headers
        )
        data = resp.json()

        assert resp.status_code == 200
        by_state = {item["estado"]: item["cantidad"] for item in data}
        assert by_state["PENDING"] == 1
        assert by_state["CONFIRMED"] == 1
        assert by_state["IN_PREP"] == 1
        assert by_state["DELIVERED"] == 1
        assert by_state["CANCELLED"] == 1

    def test_ingresos_solo_approved(
        self, db_session, client, admin_headers, producto_factory, pedido_factory
    ):
        user = _create_user(db_session, "ingresos@test.com")
        p = producto_factory(name="Ingresos P", base_price=Decimal("100"), stock=100)

        o1 = pedido_factory(usuario_id=user.id, producto_id=p.id)
        o1.state_code = "CONFIRMED"

        o2 = pedido_factory(usuario_id=user.id, producto_id=p.id)
        o2.state_code = "IN_PREP"

        o3 = pedido_factory(usuario_id=user.id, producto_id=p.id)
        o3.state_code = "DELIVERED"

        o4 = pedido_factory(usuario_id=user.id, producto_id=p.id)
        o4.state_code = "CANCELLED"

        db_session.flush()

        resp = client.get("/admin/estadisticas/ingresos", headers=admin_headers)
        data = resp.json()

        assert resp.status_code == 200
        assert float(data["total"]) == 300.0
        assert sum(float(fp["total"]) for fp in data["por_forma_pago"]) == 300.0

    def test_cancelado_no_suma(
        self, db_session, client, admin_headers, producto_factory, pedido_factory
    ):
        user = _create_user(db_session, "cancel@test.com")
        p = producto_factory(name="Cancel P", base_price=Decimal("100"), stock=100)

        o = pedido_factory(usuario_id=user.id, producto_id=p.id)
        o.state_code = "CANCELLED"

        db_session.flush()

        resp = client.get("/admin/estadisticas/ingresos", headers=admin_headers)
        data = resp.json()

        assert resp.status_code == 200
        assert float(data["total"]) == 0.0
        assert data["por_forma_pago"] == []

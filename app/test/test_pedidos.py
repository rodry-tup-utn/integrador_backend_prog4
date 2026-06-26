"""Tests del módulo de pedidos."""

from decimal import Decimal

import pytest
from fastapi import status
from sqlmodel import select

from app.modules.user.models import User, Address


def _get_user(db_session, email: str) -> User:
    return db_session.exec(select(User).where(User.email == email)).first()


def _create_address(db_session, user_id: int) -> Address:
    address = Address(
        user_id=user_id,
        alias="Casa",
        line_one="Calle Test 123",
        city="Test City",
        province="Test Province",
        zip_code="12345",
        latitude=Decimal("0.0"),
        longitude=Decimal("0.0"),
        is_main=True,
    )
    db_session.add(address)
    db_session.flush()
    return address


class TestCreateOrder:
    def test_create_order_ok(
        self, db_session, client, client_headers, producto_factory
    ):
        product = producto_factory()
        user = _get_user(db_session, "cliente_test@test.com")
        address = _create_address(db_session, user.id)  # type: ignore

        resp = client.post(
            "/order/",
            json={
                "address_id": address.id,
                "payment_method_code": "EFECTIVO",
                "items": [{"product_id": product.id, "quantity": 1}],
            },
            headers=client_headers,
        )
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        assert data["state_code"] == "PENDING"
        assert len(data["items"]) == 1
        assert data["items"][0]["product_id"] == product.id

    def test_create_order_retiro_local(
        self, db_session, client, client_headers, producto_factory
    ):
        product = producto_factory()
        user = _get_user(db_session, "cliente_test@test.com")

        resp = client.post(
            "/order/",
            json={
                "address_id": None,
                "payment_method_code": "EFECTIVO",
                "items": [{"product_id": product.id, "quantity": 1}],
            },
            headers=client_headers,
        )
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        assert data["state_code"] == "PENDING"
        assert data["address_id"] is None

    def test_create_order_insufficient_stock(
        self, db_session, client, client_headers, producto_factory
    ):
        product = producto_factory(stock=1)
        user = _get_user(db_session, "cliente_test@test.com")
        address = _create_address(db_session, user.id)  # type: ignore

        resp = client.post(
            "/order/",
            json={
                "address_id": address.id,
                "payment_method_code": "EFECTIVO",
                "items": [{"product_id": product.id, "quantity": 10}],
            },
            headers=client_headers,
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "Stock insuficiente" in resp.text


class TestAdvanceState:
    def test_advance_state_valid(
        self, db_session, client, pedidos_headers, pedido_factory, producto_factory
    ):
        product = producto_factory(stock=10)
        user = _get_user(db_session, "pedidos_test@test.com")
        order = pedido_factory(usuario_id=user.id, producto_id=product.id)

        resp = client.patch(
            f"/orders/order/{order.id}/state",
            json={"state_code": "CONFIRMED"},
            headers=pedidos_headers,
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["state_code"] == "CONFIRMED"

    def test_advance_state_skip(
        self, db_session, client, pedidos_headers, pedido_factory, producto_factory
    ):
        product = producto_factory(stock=10)
        user = _get_user(db_session, "pedidos_test@test.com")
        order = pedido_factory(usuario_id=user.id, producto_id=product.id)

        resp = client.patch(
            f"/orders/order/{order.id}/state",
            json={"state_code": "DELIVERED"},
            headers=pedidos_headers,
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_advance_state_invalid_payload(
        self, db_session, client, pedidos_headers, pedido_factory, producto_factory
    ):
        product = producto_factory(stock=10)
        user = _get_user(db_session, "pedidos_test@test.com")
        order = pedido_factory(usuario_id=user.id, producto_id=product.id)

        resp = client.patch(
            f"/orders/order/{order.id}/state",
            json={"state_code": None},
            headers=pedidos_headers,
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestCancelOrder:
    def test_cancel_own_order(
        self, db_session, client, client_headers, pedido_factory, producto_factory
    ):
        product = producto_factory(stock=10)
        user = _get_user(db_session, "cliente_test@test.com")
        order = pedido_factory(usuario_id=user.id, producto_id=product.id)

        resp = client.post(f"/order/{order.id}/cancel", headers=client_headers)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["state_code"] == "CANCELLED"


class TestOrderHistorial:
    def test_historial_append_only(
        self,
        db_session,
        client,
        client_headers,
        pedidos_headers,
        pedido_factory,
        producto_factory,
    ):
        product = producto_factory(stock=10)
        user = _get_user(db_session, "cliente_test@test.com")
        order = pedido_factory(usuario_id=user.id, producto_id=product.id)

        resp = client.get(f"/order/{order.id}", headers=client_headers)
        assert resp.status_code == status.HTTP_200_OK
        historials = resp.json()["historials"]
        assert len(historials) == 1
        assert historials[0]["state_to_code"] == "PENDING"

        client.patch(
            f"/orders/order/{order.id}/state",
            json={"state_code": "CONFIRMED"},
            headers=pedidos_headers,
        )

        client.post(f"/order/{order.id}/cancel", headers=client_headers)

        resp = client.get(f"/order/{order.id}", headers=client_headers)
        historials = resp.json()["historials"]
        assert len(historials) == 3
        assert historials[0]["state_to_code"] == "PENDING"
        assert historials[1]["state_to_code"] == "CONFIRMED"
        assert historials[2]["state_to_code"] == "CANCELLED"

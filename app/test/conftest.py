"""
tests/conftest.py
=================

Fixtures compartidos por toda la suite de tests.
"""

import os
import pytest
from decimal import Decimal
from typing import Callable
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlalchemy.pool import StaticPool
from sqlmodel import col
from app.core.config import settings
from app.core.database import get_session
from app.core.middleware import RateLimitMiddleware
from app.core.security import get_password_hash
from app.main import app
from app.modules.ingredient.models import MeasurementUnit
from app.modules.product.models import Product, ProductType
from app.modules.user.models import User, Role, UserRoleLink, Address
from app.modules.order.models import Order, StateOrder, PaymentMethod, OrderHistorial
from app.modules.order_item.models import OrderItem
from app.modules.category.models import Category
from app.modules.product_category.models import ProductCategoryLink
from sqlalchemy.ext.compiler import compiles
from sqlalchemy import ARRAY, String


@compiles(ARRAY, "sqlite")
def _compile_array_sqlite(type_, compiler, **kw):
    """SQLite no soporta ARRAY; lo tratamos como TEXT."""
    return compiler.process(String())


os.environ.setdefault("ENVIRONMENT", "test")


# ===========================================================================
# 1. ENGINE DE TEST (session scope — una vez por suite)
# ===========================================================================
@pytest.fixture(name="engine", scope="session")
def engine_fixture():
    url = settings.TEST_DATABASE_URL
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(
        url, connect_args=connect_args, poolclass=StaticPool, echo=False
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


# ===========================================================================
# 2. DB SESSION (function scope — rollback automático)
# ===========================================================================
@pytest.fixture(name="db_session", scope="function")
def db_session_fixture(engine):
    conn = engine.connect()
    trans = conn.begin()
    session = Session(bind=conn)
    session.commit = session.flush
    yield session
    session.close()
    trans.rollback()
    conn.close()


# ===========================================================================
# HELPERS DE SEMILLA
# ===========================================================================
def _seed_reference_tables(session: Session) -> None:
    """Seed datos referenciales necesarios para tests (roles, estados, pagos, categorias)."""

    for role_data in [
        {"code": "ADMIN", "name": "Administrador", "description": "Rol administrador"},
        {"code": "CLIENT", "name": "Cliente", "description": "Rol cliente"},
        {"code": "ORDERS", "name": "Pedidos", "description": "Rol pedidos"},
        {"code": "STOCK", "name": "Stock", "description": "Rol stock"},
    ]:
        if not session.exec(select(Role).where(Role.code == role_data["code"])).first():
            session.add(Role(**role_data))  # type: ignore

    for state_data in [
        {
            "code": "PENDING",
            "description": "Estamos procesando tu pedido...",
            "order": 1,
            "is_terminal": False,
        },
        {
            "code": "CONFIRMED",
            "description": "Pedido confirmado!",
            "order": 2,
            "is_terminal": False,
        },
        {
            "code": "IN_PREP",
            "description": "Estamos preparando tu pedido...",
            "order": 3,
            "is_terminal": False,
        },
        {
            "code": "DELIVERED",
            "description": "Hemos entregado tu pedido!",
            "order": 4,
            "is_terminal": True,
        },
        {
            "code": "CANCELLED",
            "description": "Pedido cancelado",
            "order": 5,
            "is_terminal": True,
        },
    ]:
        if not session.exec(
            select(StateOrder).where(StateOrder.code == state_data["code"])
        ).first():
            session.add(StateOrder(**state_data))

    for pm_data in [
        {"code": "MERCADOPAGO", "description": "MercadoPago", "available": True},
        {"code": "EFECTIVO", "description": "Efectivo", "available": True},
        {
            "code": "TRANSFERENCIA",
            "description": "Transferencia Bancarizada",
            "available": True,
        },
    ]:
        if not session.exec(
            select(PaymentMethod).where(PaymentMethod.code == pm_data["code"])
        ).first():
            session.add(PaymentMethod(**pm_data))

    for mu_data in [
        {"code": "LITER", "name": "Litro", "symbol": "L", "unit_type": "volume"},
        {"code": "GRAM", "name": "Gramo", "symbol": "g", "unit_type": "weight"},
        {"code": "UNIT", "name": "Unidad", "symbol": "ud", "unit_type": "countable"},
    ]:
        if not session.exec(
            select(MeasurementUnit).where(MeasurementUnit.code == mu_data["code"])
        ).first():
            session.add(MeasurementUnit(**mu_data))

    if not session.exec(select(Category).where(Category.name == "Comidas")).first():
        session.add(Category(name="Comidas", description="Categoria raiz para tests"))


def _create_test_admin(session: Session) -> None:
    """Crea el usuario admin en la session de TEST."""
    existing = session.exec(
        select(User).where(User.email == settings.admin_email)
    ).first()
    if existing is not None:
        return

    admin = User(
        name="Administrador",
        lastname="Sistema",
        email=settings.admin_email,
        hashed_pass=get_password_hash(settings.admin_pass),
    )
    session.add(admin)
    session.flush()

    role = session.exec(select(Role).where(Role.code == "ADMIN")).first()
    if role:
        link = UserRoleLink(
            user_id=admin.id,  # type: ignore
            role_code="ADMIN",
            assigned_by_id=admin.id,  # type: ignore
            created_at=datetime.now(timezone.utc),
        )
        session.add(link)


def _reset_rate_limit_state() -> None:
    try:
        RateLimitMiddleware.reset_all_limiters()
    except Exception:
        pass


# ===========================================================================
# 3. CLIENTE HTTP DE TEST
# ===========================================================================
@pytest.fixture(name="client", scope="function")
def client_fixture(db_session: Session):
    def get_session_override():
        return db_session

    app.dependency_overrides[get_session] = get_session_override
    _reset_rate_limit_state()
    _seed_reference_tables(db_session)
    _create_test_admin(db_session)

    with (
        patch("app.main.create_db_and_tables"),
        patch("app.main.run"),
    ):
        with TestClient(app) as client:
            yield client

    app.dependency_overrides.clear()


# ===========================================================================
# 4. HELPERS DE AUTENTICACIÓN
# ===========================================================================
def _get_admin_auth_headers(client: TestClient) -> dict:
    response = client.post(
        "/auth/login",
        data={"username": settings.admin_email, "password": settings.admin_pass},
    )
    assert response.status_code == 200, f"Login admin falló: {response.text}"
    cookie = response.cookies.get("access_token")
    assert cookie, f"Sin cookie access_token: {response.text}"
    return {"Cookie": f"access_token={cookie}"}


def _get_user_auth_headers(client: TestClient, username: str, password: str) -> dict:
    response = client.post(
        "/auth/login",
        data={"username": username, "password": password},
    )
    assert response.status_code == 200, f"Login falló para {username}: {response.text}"
    cookie = response.cookies.get("access_token")
    assert cookie, f"Sin cookie access_token para {username}: {response.text}"
    return {"Cookie": f"access_token={cookie}"}


# ===========================================================================
# 5. FIXTURES DE AUTENTICACIÓN POR ROL
# ===========================================================================
@pytest.fixture(name="admin_headers")
def admin_headers_fixture(client: TestClient) -> dict:
    return _get_admin_auth_headers(client)


@pytest.fixture(name="client_headers")
def client_headers_fixture(db_session: Session, client: TestClient) -> dict:
    user = User(
        name="Cliente",
        lastname="Test",
        email="cliente_test@test.com",
        hashed_pass=get_password_hash("TestPass123!"),
    )
    db_session.add(user)
    db_session.flush()

    role = db_session.exec(select(Role).where(Role.code == "CLIENT")).first()
    if role:
        link = UserRoleLink(
            user_id=user.id,  # type: ignore
            role_code="CLIENT",
            assigned_by_id=user.id,  # type: ignore
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(link)

    return _get_user_auth_headers(client, "cliente_test@test.com", "TestPass123!")


@pytest.fixture(name="pedidos_headers")
def pedidos_headers_fixture(db_session: Session, client: TestClient) -> dict:
    user = User(
        name="Pedidos",
        lastname="Test",
        email="pedidos_test@test.com",
        hashed_pass=get_password_hash("TestPass123!"),
    )
    db_session.add(user)
    db_session.flush()

    role = db_session.exec(select(Role).where(Role.code == "ORDERS")).first()
    if role:
        link = UserRoleLink(
            user_id=user.id,  # type: ignore
            role_code="ORDERS",
            assigned_by_id=user.id,  # type: ignore
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(link)

    return _get_user_auth_headers(client, "pedidos_test@test.com", "TestPass123!")


# ===========================================================================
# 6. FIXTURES DE FÁBRICA
# ===========================================================================
@pytest.fixture(name="producto_factory")
def producto_factory_fixture(db_session: Session) -> Callable:
    """Factory: crea un Producto con stock en la BD de test."""

    def _create(
        name: str = "Producto Test",
        base_price: Decimal = Decimal("100.00"),
        stock: int = 10,
        type: ProductType = ProductType.FINAL,
        available: bool = True,
        category_id: int | None = None,
    ) -> Product:
        product = Product(
            name=name,
            base_price=base_price,
            stock=stock,
            type=type,
            available=available,
        )
        db_session.add(product)
        db_session.flush()

        if category_id is not None:
            link = ProductCategoryLink(
                product_id=product.id,  # type: ignore
                category_id=category_id,
                is_primary=True,
            )
            db_session.add(link)

        return product

    return _create


@pytest.fixture(name="pedido_factory")
def pedido_factory_fixture(db_session: Session) -> Callable:
    """Factory: crea un Pedido en estado PENDIENTE con un DetallePedido."""

    def _create(
        usuario_id: int,
        producto_id: int,
        quantity: int = 1,
    ) -> Order:
        address = db_session.exec(
            select(Address).where(
                Address.user_id == usuario_id, col(Address.deleted_at).is_(None)
            )
        ).first()
        if not address:
            address = Address(
                user_id=usuario_id,
                alias="Casa",
                line_one="Calle Test 123",
                city="Test City",
                province="Test",
                zip_code="12345",
                latitude=Decimal("0.0"),
                longitude=Decimal("0.0"),
                is_main=True,
            )
            db_session.add(address)
            db_session.flush()

        product = db_session.get(Product, producto_id)
        assert product is not None, f"Producto {producto_id} no encontrado"

        state = db_session.exec(
            select(StateOrder).where(StateOrder.code == "PENDING")
        ).first()
        assert state is not None, "Estado PENDING no configurado"

        payment = db_session.exec(
            select(PaymentMethod).where(PaymentMethod.code == "EFECTIVO")
        ).first()
        assert payment is not None, "Método de pago EFECTIVO no configurado"

        subtotal = product.base_price * quantity

        order = Order(
            user_id=usuario_id,
            address_id=address.id,  # type: ignore
            state_code=state.code,
            payment_method_code=payment.code,
            subtotal=subtotal,
            discount=Decimal("0.00"),
            shipping_cost=Decimal("0.00"),
        )
        db_session.add(order)
        db_session.flush()

        item = OrderItem(
            order_id=order.id,  # type: ignore
            product_id=producto_id,
            quantity=quantity,
            name_snap=product.name,
            price_snap=product.base_price,
            subtotal_snap=subtotal,
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(item)

        historial = OrderHistorial(
            order_id=order.id,  # type: ignore
            state_from_code=None,
            state_to_code=state.code,
            reason="Pedido creado (test)",
        )
        db_session.add(historial)

        return order

    return _create


# ===========================================================================
# 7. FIXTURES DE DATOS (PAYLOADS)
# ===========================================================================
@pytest.fixture(name="producto_payload")
def producto_payload_fixture() -> dict:
    return {
        "name": "Laptop Test",
        "description": "Notebook de prueba",
        "base_price": 999.99,
        "stock": 10,
        "category_id": 1,
        "type": "FINAL",
    }


@pytest.fixture(name="admin_user_data")
def admin_user_data_fixture() -> dict:
    return {
        "email": settings.admin_email,
        "password": settings.admin_pass,
    }


@pytest.fixture(name="normal_user_data")
def normal_user_data_fixture() -> dict:
    return {
        "name": "Test",
        "lastname": "User",
        "email": "testuser@example.com",
        "password": "TestPass123!",
    }


@pytest.fixture(name="normal_user")
def normal_user_fixture(client: TestClient, normal_user_data: dict) -> dict:
    response = client.post("/user/", json=normal_user_data)
    assert response.status_code == 201, f"Setup normal_user falló: {response.json()}"
    return response.json()


@pytest.fixture(name="user_auth_headers")
def user_auth_headers_fixture(client: TestClient, normal_user: dict) -> dict:
    return _get_user_auth_headers(client, normal_user["email"], "TestPass123!")

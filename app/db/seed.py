from sqlmodel import Session, select
from app.core.database import engine, create_db_and_tables
from app.core.security import get_password_hash
from app.modules.user.models import Role, User, UserRoleLink, Address
from app.modules.product_category.models import ProductCategoryLink
from app.modules.product_ingredient.models import ProductIngredient
from app.modules.product.models import Product
from app.modules.ingredient.models import Ingredient
from datetime import datetime, timezone
from app.modules.category.models import Category
from app.modules.order.models import StateOrder, PaymentMethod
from app.modules.payments.models import Payment

datetime_now = datetime.now(timezone.utc)

ROLES = [
    {
        "code": "ADMIN",
        "name": "Administrador",
        "description": "Usuario Administrador de Sistema",
    },
    {
        "code": "STOCK",
        "name": "Stock",
        "description": "Usuario para control de Stock",
    },
    {
        "code": "ORDERS",
        "name": "Pedidos",
        "description": "Usuario para control de Pedidos",
    },
    {
        "code": "CLIENT",
        "name": "Cliente",
        "description": "Usuario Cliente",
    },
]

USERS = [
    {
        "name": "Administrador",
        "lastname": "Usuario",
        "email": "admin@admin.com",
        "hashed_pass": get_password_hash("admin1234"),
    },
    {
        "name": "Stock",
        "lastname": "Usuario",
        "email": "stock@stock.com",
        "hashed_pass": get_password_hash("stock1234"),
    },
    {
        "name": "Pedidos",
        "lastname": "Usuario",
        "email": "pedidos@pedidos.com",
        "hashed_pass": get_password_hash("pedidos1234"),
    },
    {
        "name": "Cliente",
        "lastname": "Usuario",
        "email": "cliente@cliente.com",
        "hashed_pass": get_password_hash("cliente1234"),
    },
]

ADRESSES = [
    {
        "user_id": "4",
        "alias": "Casa",
        "line_one": "Calle Falsa 123",
        "city": "Springfield",
        "province": "Fake Province",
        "zip_code": "12345",
        "latitude": 50.0,
        "longitude": 120.0,
        "is_main": True,
    }
]

CATEGORIES = [
    # --------------------
    # COMIDAS
    # --------------------
    {
        "name": "Comidas",
        "description": "Todas las comidas",
        "image_url": None,
        "parent_name": None,
    },
    {
        "name": "Pizzas",
        "description": "Pizzas tradicionales y especiales",
        "image_url": None,
        "parent_name": "Comidas",
    },
    {
        "name": "Empanadas",
        "description": "Empanadas horneadas y fritas",
        "image_url": None,
        "parent_name": "Comidas",
    },
    {
        "name": "Hamburguesas",
        "description": "Hamburguesas artesanales",
        "image_url": None,
        "parent_name": "Comidas",
    },
    {
        "name": "Milanesas",
        "description": "Milanesas con diferentes guarniciones",
        "image_url": None,
        "parent_name": "Comidas",
    },
    {
        "name": "Pastas",
        "description": "Pastas caseras",
        "image_url": None,
        "parent_name": "Comidas",
    },
    # --------------------
    # SUBCATEGORIAS PIZZAS
    # --------------------
    {
        "name": "Pizza Napolitana",
        "description": "Pizza con tomate y ajo",
        "image_url": None,
        "parent_name": "Pizzas",
    },
    {
        "name": "Pizza Muzzarella",
        "description": "Pizza clásica de muzzarella",
        "image_url": None,
        "parent_name": "Pizzas",
    },
    {
        "name": "Pizza Especial",
        "description": "Pizza con ingredientes especiales",
        "image_url": None,
        "parent_name": "Pizzas",
    },
    # --------------------
    # SUBCATEGORIAS EMPANADAS
    # --------------------
    {
        "name": "Empanadas de Carne",
        "description": "Empanadas rellenas de carne",
        "image_url": None,
        "parent_name": "Empanadas",
    },
    {
        "name": "Empanadas de Pollo",
        "description": "Empanadas rellenas de pollo",
        "image_url": None,
        "parent_name": "Empanadas",
    },
    {
        "name": "Empanadas Vegetarianas",
        "description": "Empanadas sin carne",
        "image_url": None,
        "parent_name": "Empanadas",
    },
    # --------------------
    # BEBIDAS
    # --------------------
    {
        "name": "Bebidas",
        "description": "Todas las bebidas",
        "image_url": None,
        "parent_name": None,
    },
    {
        "name": "Gaseosas",
        "description": "Bebidas gaseosas",
        "image_url": None,
        "parent_name": "Bebidas",
    },
    {
        "name": "Aguas",
        "description": "Aguas minerales y saborizadas",
        "image_url": None,
        "parent_name": "Bebidas",
    },
    {
        "name": "Jugos",
        "description": "Jugos naturales y procesados",
        "image_url": None,
        "parent_name": "Bebidas",
    },
    {
        "name": "Cervezas",
        "description": "Cervezas nacionales e importadas",
        "image_url": None,
        "parent_name": "Bebidas",
    },
    # --------------------
    # POSTRES
    # --------------------
    {
        "name": "Postres",
        "description": "Postres y cosas dulces",
        "image_url": None,
        "parent_name": None,
    },
    {
        "name": "Helados",
        "description": "Helados artesanales",
        "image_url": None,
        "parent_name": "Postres",
    },
    {
        "name": "Tortas",
        "description": "Tortas y tartas dulces",
        "image_url": None,
        "parent_name": "Postres",
    },
    {
        "name": "Flanes",
        "description": "Flanes caseros",
        "image_url": None,
        "parent_name": "Postres",
    },
    # --------------------
    # DESAYUNO Y MERIENDA
    # --------------------
    {
        "name": "Desayuno y Merienda",
        "description": "Opciones para desayuno y merienda",
        "image_url": None,
        "parent_name": None,
    },
    {
        "name": "Cafetería",
        "description": "Café y bebidas calientes",
        "image_url": None,
        "parent_name": "Desayuno y Merienda",
    },
    {
        "name": "Medialunas",
        "description": "Medialunas dulces y saladas",
        "image_url": None,
        "parent_name": "Desayuno y Merienda",
    },
    {
        "name": "Sandwiches",
        "description": "Sandwiches tostados y fríos",
        "image_url": None,
        "parent_name": "Desayuno y Merienda",
    },
]

ORDER_STATES = [
    {
        "code": "PENDING",
        "description": "Estamos procesando tu pedido...",
        "order": 1,
        "is_terminal": False,
    },
    {
        "code": "CONFIRMED",
        "description": "Pedido confirmado! Proximamente sera preparado...",
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
]

PAYMENT_METHODS = [
    {
        "code": "MERCADOPAGO",
        "description": "Plataforma de pago de MercadoPago",
        "available": True,
    },
    {"code": "EFECTIVO", "description": "Pago en efectivo", "available": True},
    {
        "code": "TRANSFERENCIA",
        "description": "Pago con transferencia Bancarizada",
        "available": True,
    },
]


def run() -> None:
    create_db_and_tables()

    with Session(engine) as session:
        for data_adress in ROLES:
            existing = session.exec(
                select(Role).where(Role.code == data_adress["code"])
            ).first()

            if existing:
                print(f"  [=] Ya existe: {data_adress['code']}")
            else:
                role = Role(
                    code=data_adress["code"],
                    name=data_adress["name"],
                    description=data_adress["description"],
                )
                session.add(role)
                print(f"  [+] Creado:    {data_adress['name']})")

        for user in USERS:
            existing = session.exec(
                select(User).where(User.email == user["email"])
            ).first()

            if existing:
                print(f"  [=] Ya existe: {user['email']}")
            else:
                user = User(
                    name=user["name"],
                    lastname=user["lastname"],
                    email=user["email"],
                    hashed_pass=user["hashed_pass"],
                    created_at=datetime_now,
                )
                session.add(user)

        for data_adress in ADRESSES:
            existing = session.exec(
                select(Address).where(Address.line_one == data_adress["line_one"])
            ).first()
            if existing:
                print(f"Ya existe la direccion id {data_adress["line_one"]}")
            else:
                adress = Address(
                    user_id=data_adress["user_id"],
                    alias=data_adress["alias"],
                    line_one=data_adress["line_one"],
                    city=data_adress["city"],
                    province=data_adress["province"],
                    zip_code=data_adress["zip_code"],
                    latitude=data_adress["latitude"],
                    is_main=data_adress["is_main"],
                    longitude=data_adress["longitude"],
                )
                session.add(adress)
                print("Direccion agregada")
            session.commit()

        # refrescar usuarios/roles desde DB
        users = session.exec(select(User)).all()
        roles = session.exec(select(Role)).all()

    role_map = {r.code: r for r in roles}
    user_map = {u.email: u for u in users}

    # --------------------
    # RELACIONES USER - ROLE
    # --------------------

    relations = [
        ("admin@admin.com", "ADMIN"),
        ("stock@stock.com", "STOCK"),
        ("pedidos@pedidos.com", "ORDERS"),
        ("cliente@cliente.com", "CLIENT"),
    ]

    for email, role_code in relations:

        user = user_map[email]
        role = role_map[role_code]

        existing_link = session.exec(
            select(UserRoleLink).where(
                UserRoleLink.user_id == user.id,
                UserRoleLink.role_code == role.code,
                UserRoleLink.expires_at == None,
            )
        ).first()

        if not existing_link:
            link = UserRoleLink(
                user_id=user.id,
                role_code=role.code,
                assigned_by_id=user.id,
                created_at=datetime.now(timezone.utc),
            )

            session.add(link)
            print(f"  [+] Relación {email} -> {role_code}")

        else:
            print(f"  [=] Ya existe relación {email} -> {role_code}")

        session.commit()

    category_map = {}
    for data_category in CATEGORIES:

        existing = session.exec(
            select(Category).where(Category.name == data_category["name"])
        ).first()

        if existing:
            print(f"  [=] Ya existe categoria: {data_category['name']}")
            category_map[data_category["name"]] = existing
            continue

        parent = None

        if data_category["parent_name"]:
            parent = session.exec(
                select(Category).where(Category.name == data_category["parent_name"])
            ).first()

        category = Category(
            name=data_category["name"],
            description=data_category["description"],
            image_url=data_category["image_url"],
            parent_id=parent.id if parent else None,
        )

        session.add(category)
        session.flush()

        session.commit()

        category_map[data_category["name"]] = category

        print(f"  [+] Categoria creada: {category.name}")

    for state in ORDER_STATES:
        existing = session.exec(
            select(StateOrder).where(StateOrder.code == state["code"])
        ).first()

        if existing:
            print(f"Ya existe el estado {state["code"]}")
        else:
            state = StateOrder(
                code=state["code"],
                description=state["description"],
                order=state["order"],
                is_terminal=state["is_terminal"],
            )

            session.add(state)

        session.commit()

    for payment in PAYMENT_METHODS:
        existing = session.exec(
            select(PaymentMethod).where(PaymentMethod.code == payment["code"])
        ).first()

        if existing:
            print(f"Ya existe el metodo de pago {payment["code"]}")
        else:
            payment = PaymentMethod(
                code=payment["code"],
                description=payment["description"],
                available=payment["available"],
            )

            session.add(payment)

        session.commit()


if __name__ == "__main__":
    run()

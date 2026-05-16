from sqlmodel import Session, select
from app.core.database import engine, create_db_and_tables
from app.core.security import get_password_hash
from app.modules.user.models import Role, User, UserRoleLink
from datetime import datetime, timezone

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


def run() -> None:
    print("=== Seed de Usuarios y Roles) ===")
    create_db_and_tables()

    with Session(engine) as session:
        for data in ROLES:
            existing = session.exec(
                select(Role).where(Role.code == data["code"])
            ).first()

            if existing:
                print(f"  [=] Ya existe: {data['code']}")
            else:
                role = Role(
                    code=data["code"],
                    name=data["name"],
                    description=data["description"],
                )
                session.add(role)
                print(f"  [+] Creado:    {data['name']})")

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


if __name__ == "__main__":
    run()

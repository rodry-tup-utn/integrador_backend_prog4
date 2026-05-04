from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.database import create_db_and_tables
from app.modules.category.router import router as public_category_router
from app.modules.category.router import admin_router as admin_category_router
from app.modules.product.router import router as public_product_router
from app.modules.product.router import admin_router as admin_product_router
from app.modules.ingredient.router import router as public_ingredient_router
from app.modules.ingredient.router import admin_router as admin_ingredient_router
from app.modules.product_ingredient.router import router as product_ingredient_router
from app.modules.user.router import admin_router as admin_user_router
from app.modules.user.router import public_router as public_user_router
from app.modules.user.router import user_router
from app.modules.auth.router import router as auth_router
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(
    title="API Productos, Categoria, Ingredientes y Usuarios",
    description="Entrega Primer Parcial Backend Programacion IV",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(admin_category_router)
app.include_router(public_category_router)
app.include_router(public_product_router)
app.include_router(admin_product_router)
app.include_router(public_ingredient_router)
app.include_router(admin_ingredient_router)
app.include_router(product_ingredient_router)
app.include_router(admin_user_router)
app.include_router(public_user_router)
app.include_router(auth_router)
app.include_router(user_router)

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

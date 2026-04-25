from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.database import create_db_and_tables
from app.modules.health.router import router as health_router
from app.modules.category.models import Category
from app.modules.product.models import Product
from app.modules.category.router import router as public_category_router
from app.modules.category.router import admin_router as admin_category_router
from app.modules.product.router import router as public_product_router
from app.modules.product.router import admin_router as admin_product_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(
    title="API Productos, Categoria e Ingredientes",
    description="Entrega Primer Parcial Backend Programacion IV",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(admin_category_router)
app.include_router(public_category_router)
app.include_router(public_product_router)
app.include_router(admin_product_router)

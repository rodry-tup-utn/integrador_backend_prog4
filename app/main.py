from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.database import create_db_and_tables
from app.modules.health.router import router as health_router
from app.modules.category.models import Category


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

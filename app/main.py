from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.database import create_db_and_tables
from app.modules.category.router import router as public_category_router
from app.modules.category.router import admin_router as admin_category_router
from app.modules.product.router import router as public_product_router
from app.modules.product.router import admin_router as admin_product_router
from app.modules.product.router import stock_router as stock_product_router
from app.modules.ingredient.router import router as public_ingredient_router
from app.modules.ingredient.router import admin_router as admin_ingredient_router
from app.modules.product_ingredient.router import router as product_ingredient_router
from app.modules.product_ingredient.router import (
    stock_router as stock_product_ingredient_router,
)
from app.modules.user.router import admin_router as admin_user_router
from app.modules.user.router import public_router as public_user_router
from app.modules.user.router import user_router
from app.modules.auth.router import router as auth_router
from app.modules.estadisticas.router import router as estadisticas_router
from app.modules.order.router import user_router as user_order_router
from app.modules.order.router import admin_router as admin_order_router
from app.modules.order.router import orders_router
from app.modules.websocket.router import router as ws_router
from app.modules.payments.router import router as public_payment_router
from app.modules.payments.router import admin_router as admin_payment_router
from fastapi.middleware.cors import CORSMiddleware
from app.core.exceptions import register_exception_handlers
from app.core.middleware import LoggingMiddleware, TimingMiddleware, RateLimitMiddleware
from app.core.config import settings
from app.core.logger import setup_logging
from app.db.seed import run
from app.core.cloudinary.client import init_cloudinary
from app.modules.uploads.router import router as upload_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    setup_logging()
    run()
    init_cloudinary()
    yield


app = FastAPI(
    title="API Productos, Categoria, Ingredientes y Usuarios",
    description="Entrega Primer Parcial Backend Programacion IV",
    version="1.0.0",
    lifespan=lifespan,
)

register_exception_handlers(app)

app.include_router(admin_category_router)
app.include_router(public_category_router)
app.include_router(public_product_router)
app.include_router(admin_product_router)
app.include_router(stock_product_router)
app.include_router(public_ingredient_router)
app.include_router(admin_ingredient_router)
app.include_router(product_ingredient_router)
app.include_router(stock_product_ingredient_router)
app.include_router(admin_user_router)
app.include_router(public_user_router)
app.include_router(auth_router)
app.include_router(estadisticas_router)
app.include_router(user_router)
app.include_router(user_order_router)
app.include_router(admin_order_router)
app.include_router(orders_router)
app.include_router(public_payment_router)
app.include_router(admin_payment_router)
app.include_router(ws_router)
app.include_router(upload_router)

app.add_middleware(TimingMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(LoggingMiddleware, log_body=False)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

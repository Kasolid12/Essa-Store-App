"""
Yazmina Hijab Web — FastAPI Application.

Entry point: run with `uvicorn app.main:app --reload`.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import engine, Base
from .auth import router as auth_router
from .routers.dashboard import router as dashboard_router
from .routers.sku import router as sku_router
from .routers.person import router as person_router
from .routers.modal_operasional import router as modal_op_router
from .routers.pengeluaran_offline import router as pengeluaran_router
from .routers.hasil_cutting import router as hasil_cutting_router
from .routers.distribusi_cutting import router as distribusi_cutting_router
from .routers.hutang import router as hutang_router
from .routers.gaji import router as gaji_router
from .routers.bon import router as bon_router
from .routers.client import router as client_router
from .routers.invoice import router as invoice_router
from .routers.profit import router as profit_router
from .routers.stock import router as stock_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create tables (dev convenience). Production uses Alembic."""
    Base.metadata.create_all(bind=engine)
    print(f"[OK] {settings.APP_NAME} v{settings.APP_VERSION} started")
    yield
    print(f"[OK] {settings.APP_NAME} shut down")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────
origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(sku_router)
app.include_router(person_router)
app.include_router(modal_op_router)
app.include_router(pengeluaran_router)
app.include_router(hasil_cutting_router)
app.include_router(distribusi_cutting_router)
app.include_router(hutang_router)
app.include_router(gaji_router)
app.include_router(bon_router)
app.include_router(client_router)
app.include_router(invoice_router)
app.include_router(profit_router)
app.include_router(stock_router)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}

"""
main.py — Точка входа FastAPI приложения.

Запуск:
    cd pyro-halo
    uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

Swagger UI: http://localhost:8000/docs
ReDoc:       http://localhost:8000/redoc
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.database import init_db
from backend.routers.analyze import router as analyze_router
from backend.routers.generate import router as generate_router
from backend.routers.aggregate import router as aggregate_router

# ── Логирование ───────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan: инициализация БД при старте ────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Запуск приложения (режим: %s)", settings.app_mode.upper())
    await init_db()
    logger.info("✅ База данных инициализирована")
    yield
    logger.info("🛑 Приложение остановлено")


# ── FastAPI App ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="AI Resume Tailor",
    description=(
        "Автоматизированная система тейлоринга резюме и генерации сопроводительных писем "
        "на основе Gemini AI. Отслеживает историю откликов в SQLite."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Роутеры ──────────────────────────────────────────────────────────────────
app.include_router(analyze_router)
app.include_router(generate_router)
app.include_router(aggregate_router)


# ── Health check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"], summary="Проверка работоспособности")
async def health():
    return {
        "status": "ok",
        "mode": settings.app_mode,
        "gemini_key_set": settings.gemini_api_key != "NOT_SET",
        "google_docs_template": settings.gdoc_template_id,
    }

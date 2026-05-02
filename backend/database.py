"""
database.py — Инициализация SQLAlchemy + async SQLite.
Предоставляет get_db() dependency для FastAPI.

Путь к БД вычисляется относительно этого файла, чтобы сервер
работал корректно из любой рабочей директории (backend/ или корня).
"""
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from backend.config import settings

# Абсолютный путь к файлу БД рядом с этим модулем
_DB_DIR = Path(__file__).parent / "data"
_DB_DIR.mkdir(parents=True, exist_ok=True)
_DB_PATH = _DB_DIR / "applications.db"

# Если в .env задан database_url — используем его, иначе — дефолтный абсолютный
_db_url = settings.database_url
if _db_url == "sqlite+aiosqlite:///./backend/data/applications.db":
    _db_url = f"sqlite+aiosqlite:///{_DB_PATH}"

# Движок — async SQLite через aiosqlite
engine = create_async_engine(
    _db_url,
    echo=settings.debug,   # SQL-лог в консоль при debug=True
    future=True,
)

# Фабрика сессий
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей."""
    pass


async def init_db() -> None:
    """Создаёт все таблицы при первом запуске (если не существуют)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """
    FastAPI dependency: предоставляет async-сессию и
    гарантирует её закрытие после запроса.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

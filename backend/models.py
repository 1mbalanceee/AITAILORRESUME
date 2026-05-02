"""
models.py — ORM-модели SQLAlchemy.
Единственная таблица: Application — история всех попыток отклика.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class Application(Base):
    """
    Запись о каждой проанализированной вакансии.
    Обновляется по мере продвижения (analyzed → tailored → applied).
    """
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ── Временны́е метки ───────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # ── Информация о вакансии ──────────────────────────────────────────────────
    job_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    job_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    jd_raw: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Полный текст JD
    applicants_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Количество откликов

    # ── Результат анализа Gemini ───────────────────────────────────────────────
    match_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0.0 – 1.0
    match_report: Mapped[Optional[str]] = mapped_column(Text, nullable=True)    # JSON blob
    work_mode: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # remote/hybrid/onsite
    location_req: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    experience_gap: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Статус заявки ─────────────────────────────────────────────────────────
    # analyzed → tailored → applied → rejected / offer
    status: Mapped[str] = mapped_column(String(50), default="analyzed", nullable=False)
    kanban_status: Mapped[str] = mapped_column(String(50), default="wishlist", nullable=False)

    # ── Результат генерации ───────────────────────────────────────────────────
    gdoc_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cover_letter: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tailoring_report: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # JSON blob

    # ── Заметки пользователя ──────────────────────────────────────────────────
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<Application id={self.id} company={self.company!r} score={self.match_score}>"

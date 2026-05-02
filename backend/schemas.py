"""
schemas.py — Pydantic-схемы для запросов и ответов FastAPI.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, HttpUrl, Field


# ══════════════════════════════════════════════════════════════════════════════
# /analyze-job
# ══════════════════════════════════════════════════════════════════════════════

class AnalyzeJobRequest(BaseModel):
    """Входные данные для анализа вакансии."""
    jd_url: Optional[str] = Field(None, description="URL страницы вакансии")
    jd_text: Optional[str] = Field(None, description="Текст описания вакансии напрямую")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"jd_url": "https://hh.ru/vacancy/12345678"},
                {"jd_text": "We are looking for a Senior Product Manager with 3+ years of experience..."},
            ]
        }
    }


class MatchMarkers(BaseModel):
    """Маркеры, извлечённые Gemini из описания вакансии."""
    work_mode: Optional[str] = Field(None, description="remote / hybrid / onsite")
    location: Optional[str] = Field(None, description="Требуемая локация")
    experience_gap: Optional[str] = Field(None, description="Несоответствие по опыту")
    salary_range: Optional[str] = Field(None, description="Вилка зарплаты если указана")
    relocation_required: bool = False
    visa_sponsorship: bool = False


class AnalyzeJobResponse(BaseModel):
    """Ответ с результатом анализа вакансии."""
    application_id: int = Field(..., description="ID записи в БД")
    match: bool = Field(..., description="True = подходит, False = критические пробелы")
    score: float = Field(..., ge=0.0, le=1.0, description="Процент совпадения 0.0–1.0")
    job_title: Optional[str] = None
    company: Optional[str] = None
    markers: MatchMarkers
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    applicants_count: Optional[int] = Field(None, description="Количество откликнувшихся")
    recommendation: str = Field(..., description="Краткий вывод Gemini")


# ══════════════════════════════════════════════════════════════════════════════
# /generate-resume
# ══════════════════════════════════════════════════════════════════════════════

class GenerateResumeRequest(BaseModel):
    """Запрос на генерацию тейлорированного резюме."""
    application_id: int = Field(..., description="ID ранее проанализированной вакансии")
    approved: bool = Field(True, description="Пользователь подтвердил генерацию")
    custom_note: Optional[str] = Field(
        None,
        description="Дополнительный контекст для Gemini (например, 'акцент на Python')"
    )


class ResumeChange(BaseModel):
    """Детали изменения конкретного пункта резюме."""
    original: str
    tailored: str
    reason: Optional[str] = None

class GenerateResumeResponse(BaseModel):
    """Ответ с ссылкой на сгенерированный Google Doc."""
    application_id: int
    gdoc_url: Optional[str] = Field(None, description="Ссылка на Google Doc (None в mock-режиме)")
    cover_letter_preview: str = Field(..., description="Первые 500 символов сопроводительного письма")
    changes: List[ResumeChange] = Field(default_factory=list, description="Список изменений в буллетах")
    tailored_bullets_count: int = Field(..., description="Количество переписанных пунктов")
    status: str = Field(..., description="Статус: tailored / error")


# ══════════════════════════════════════════════════════════════════════════════
# /applications (история)
# ══════════════════════════════════════════════════════════════════════════════

class ApplicationOut(BaseModel):
    """Схема для чтения записей из истории."""
    id: int
    created_at: datetime
    job_title: Optional[str]
    company: Optional[str]
    job_url: Optional[str]
    match_score: Optional[float]
    work_mode: Optional[str]
    status: str
    gdoc_url: Optional[str]
    applicants_count: Optional[int]

    model_config = {"from_attributes": True}


class ApplicationUpdate(BaseModel):
    """Частичное обновление записи (статус, заметки)."""
    status: Optional[str] = None
    notes: Optional[str] = None

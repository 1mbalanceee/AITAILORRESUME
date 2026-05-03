"""
analyze.py — Роутер для анализа вакансий.
Эндпоинт: POST /analyze-job
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import Application
from backend.schemas import AnalyzeJobRequest, AnalyzeJobResponse, MatchMarkers
from backend.services.gemini_service import analyze_match
from backend.services.jd_parser import clean_jd_text, fetch_jd_from_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analyze-job", tags=["Analysis"])


@router.post("", response_model=AnalyzeJobResponse, summary="Анализ вакансии на совпадение с резюме")
async def analyze_job(
    body: AnalyzeJobRequest,
    db: AsyncSession = Depends(get_db),
) -> AnalyzeJobResponse:
    """
    Принимает URL или текст вакансии, сравнивает с master_resume.json через Gemini,
    сохраняет результат в SQLite и возвращает отчёт о совпадении.
    """
    # 1. Получить текст JD
    if not body.jd_url and not body.jd_text:
        raise HTTPException(
            status_code=422,
            detail="Необходимо передать jd_url или jd_text.",
        )

    applicants_count = None
    if body.jd_url:
        jd_text, applicants_count = await fetch_jd_from_url(body.jd_url)
        if not jd_text:
            raise HTTPException(
                status_code=422,
                detail=f"Не удалось извлечь текст вакансии с URL: {body.jd_url}. "
                       "Попробуйте вставить текст вакансии напрямую через jd_text.",
            )
    else:
        jd_text = clean_jd_text(body.jd_text)

    # 2. Вызов Gemini / Mock (передаем количество откликов для анализа конкуренции)
    logger.info("Запуск анализа вакансии, длина JD: %d символов, откликов: %s", len(jd_text), applicants_count)
    result = await analyze_match(jd_text, applicants_count=applicants_count)

    # 3. Сохранение в БД
    app = Application(
        job_title=result.get("job_title"),
        company=result.get("company"),
        job_url=body.jd_url,
        jd_raw=jd_text,
        applicants_count=applicants_count,
        match_score=result.get("score"),
        match_report=json.dumps(result, ensure_ascii=False),
        work_mode=result.get("markers", {}).get("work_mode"),
        location_req=result.get("markers", {}).get("location"),
        experience_gap=result.get("markers", {}).get("experience_gap"),
        salary_range=result.get("markers", {}).get("salary_range"),
        status="analyzed",
    )
    db.add(app)
    await db.flush()
    await db.refresh(app)

    logger.info("Сохранена запись Application id=%d, score=%.2f", app.id, app.match_score or 0)

    # 4. Формирование ответа
    markers_data = result.get("markers", {})
    return AnalyzeJobResponse(
        application_id=app.id,
        match=result.get("match", False),
        score=result.get("score", 0.0),
        job_title=result.get("job_title"),
        company=result.get("company"),
        markers=MatchMarkers(**markers_data),
        matched_skills=result.get("matched_skills", []),
        missing_skills=result.get("missing_skills", []),
        applicants_count=app.applicants_count,
        recommendation=result.get("recommendation", ""),
    )

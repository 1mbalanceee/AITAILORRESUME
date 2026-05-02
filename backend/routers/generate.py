"""
generate.py — Роутер для генерации тейлорированного резюме.
Эндпоинты:
  POST /generate-resume         — генерация резюме + Google Doc
  GET  /applications            — история всех попыток
  PATCH /applications/{id}      — обновить статус / заметки
"""
import json
import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import Application
from backend.schemas import ApplicationOut, ApplicationUpdate, GenerateResumeRequest, GenerateResumeResponse
from backend.services.gemini_service import generate_tailored_resume
from backend.services.gdocs_service import create_resume_doc

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Generation & History"])

MASTER_RESUME_PATH = Path(__file__).parent.parent / "data" / "master_resume.json"


def _load_resume() -> dict:
    with open(MASTER_RESUME_PATH, encoding="utf-8") as f:
        return json.load(f)


# ══════════════════════════════════════════════════════════════════════════════
# POST /generate-resume
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/generate-resume",
    response_model=GenerateResumeResponse,
    summary="Сгенерировать тейлорированное резюме и Google Doc",
)
async def generate_resume(
    body: GenerateResumeRequest,
    db: AsyncSession = Depends(get_db),
) -> GenerateResumeResponse:
    """
    На основе ранее проанализированной вакансии (application_id) генерирует:
    - Тейлорированные буллеты и саммари
    - Сопроводительное письмо
    - Google Doc (в live-режиме)

    Обновляет запись в SQLite: gdoc_url, cover_letter, status → tailored.
    """
    # 1. Достать запись из БД
    app = await db.get(Application, body.application_id)
    if not app:
        raise HTTPException(status_code=404, detail=f"Вакансия id={body.application_id} не найдена")

    if not app.jd_raw:
        raise HTTPException(status_code=422, detail="Текст вакансии отсутствует в записи")

    # 2. Gemini: тейлоринг
    logger.info("Генерация резюме для application_id=%d", body.application_id)
    tailored = await generate_tailored_resume(
        jd_text=app.jd_raw,
        custom_note=body.custom_note or "",
    )

    # 3. Google Docs: создать документ
    resume = _load_resume()
    gdoc_url = await create_resume_doc(
        tailored_data=tailored,
        resume_data=resume,
        job_title=app.job_title or "Вакансия",
    )

    # 4. Обновить запись в БД
    app.gdoc_url = gdoc_url
    app.cover_letter = tailored.get("cover_letter", "")
    app.tailoring_report = json.dumps(tailored, ensure_ascii=False)
    app.status = "tailored"
    await db.flush()

    cover_preview = (tailored.get("cover_letter") or "")[:500]
    bullets_count = len(tailored.get("tailored_bullets", []))

    logger.info("Резюме сгенерировано, doc=%s, bullets=%d", gdoc_url, bullets_count)

    return GenerateResumeResponse(
        application_id=body.application_id,
        gdoc_url=gdoc_url,
        cover_letter_preview=cover_preview,
        changes=tailored.get("changes", []),
        tailored_bullets_count=bullets_count,
        status="tailored",
    )


# ══════════════════════════════════════════════════════════════════════════════
# GET /applications — история
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/applications",
    response_model=List[ApplicationOut],
    summary="История всех откликов",
)
async def get_applications(
    db: AsyncSession = Depends(get_db),
) -> List[ApplicationOut]:
    result = await db.execute(
        select(Application).order_by(Application.created_at.desc())
    )
    return result.scalars().all()


# ══════════════════════════════════════════════════════════════════════════════
# GET /applications/{id} — детали
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/applications/{application_id}",
    response_model=dict,  # Возвращаем расширенные данные, включая отчёт
    summary="Получить полные детали одного отклика",
)
async def get_application(
    application_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Возвращает полную информацию об отклике, включая JD и отчёт."""
    app = await db.get(Application, application_id)
    if not app:
        raise HTTPException(status_code=404, detail=f"Запись id={application_id} не найдена")
    
    # Мы возвращаем dict, чтобы включить поля, которых нет в ApplicationOut
    # (например jd_raw, match_report)
    import ast
    try:
        report = ast.literal_eval(app.match_report) if app.match_report else {}
    except:
        report = {}

    try:
        tailoring = json.loads(app.tailoring_report) if app.tailoring_report else {}
    except:
        tailoring = {}

    # Merge tailoring data into report for UI consumption
    if tailoring:
        report.update({
            "changes": tailoring.get("changes", []),
            "bullets_count": tailoring.get("bullets_count", 0),
        })

    return {
        "id": app.id,
        "created_at": app.created_at,
        "job_title": app.job_title,
        "company": app.company,
        "job_url": app.job_url,
        "match_score": app.match_score,
        "work_mode": app.work_mode,
        "status": app.status,
        "kanban_status": app.kanban_status or "wishlist",
        "gdoc_url": app.gdoc_url,
        "cover_letter": app.cover_letter,
        "jd_raw": app.jd_raw,
        "report": report
    }


# ══════════════════════════════════════════════════════════════════════════════
# PATCH /applications/{id} — обновить статус / заметки
# ══════════════════════════════════════════════════════════════════════════════

@router.patch(
    "/applications/{application_id}",
    response_model=ApplicationOut,
    summary="Обновить статус или заметки по отклику",
)
async def update_application(
    application_id: int,
    body: ApplicationUpdate,
    db: AsyncSession = Depends(get_db),
) -> ApplicationOut:
    """
    Позволяет вручную обновить статус отклика (например, applied, rejected, offer)
    и добавить заметки.
    """
    app = await db.get(Application, application_id)
    if not app:
        raise HTTPException(status_code=404, detail=f"Вакансия id={application_id} не найдена")

    if body.status is not None:
        valid_statuses = {"analyzed", "tailored", "applied", "rejected", "offer", "archived"}
        if body.status not in valid_statuses:
            raise HTTPException(
                status_code=422,
                detail=f"Недопустимый статус. Доступные: {valid_statuses}",
            )
        app.status = body.status

    if body.kanban_status is not None:
        valid_kanban_statuses = {"wishlist", "applied", "interview", "offer", "rejected"}
        if body.kanban_status not in valid_kanban_statuses:
            raise HTTPException(
                status_code=422,
                detail=f"Недопустимый kanban статус. Доступные: {valid_kanban_statuses}",
            )
        app.kanban_status = body.kanban_status

    if body.notes is not None:
        app.notes = body.notes

    await db.flush()
    await db.refresh(app)
    return app


@router.patch(
    "/api/applications/{application_id}/status",
    response_model=ApplicationOut,
    summary="Обновить kanban статус отклика",
)
async def update_kanban_status(
    application_id: int,
    body: ApplicationUpdate,
    db: AsyncSession = Depends(get_db),
) -> ApplicationOut:
    """Специальный эндпоинт для обновления статуса на канбан-доске."""
    return await update_application(application_id, body, db)


# ══════════════════════════════════════════════════════════════════════════════
# DELETE /applications/{id}
# ══════════════════════════════════════════════════════════════════════════════

@router.delete(
    "/applications/{application_id}",
    summary="Удалить запись из истории",
)
async def delete_application(
    application_id: int,
    db: AsyncSession = Depends(get_db),
):
    app = await db.get(Application, application_id)
    if not app:
        raise HTTPException(status_code=404, detail=f"Запись id={application_id} не найдена")
    
    await db.delete(app)
    await db.flush()
    return {"status": "deleted"}

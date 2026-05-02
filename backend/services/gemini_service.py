"""
gemini_service.py — Клиент для Gemini AI.

Режим работы определяется APP_MODE в .env:
  - "mock": возвращает статичные заглушки, без вызова API
  - "live": реальные запросы к Gemini 1.5 Pro

При переключении на "live" достаточно только указать GEMINI_API_KEY в .env.
"""
import json
import logging
from pathlib import Path
from typing import Any, Optional

from backend.config import settings

logger = logging.getLogger(__name__)

# Папка с промптами
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _load_prompt(name: str) -> str:
    """Загружает текст промпта из файла prompts/{name}.txt"""
    path = PROMPTS_DIR / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Промпт не найден: {path}")
    return path.read_text(encoding="utf-8")


def _load_master_resume() -> dict:
    """Загружает master_resume.json."""
    resume_path = Path(__file__).parent.parent / "data" / "master_resume.json"
    with open(resume_path, encoding="utf-8") as f:
        return json.load(f)


# ── Mock-ответы (для разработки без API-ключа) ─────────────────────────────

_MOCK_MATCH_RESULT = {
    "match": True,
    "score": 0.78,
    "job_title": "Project Manager (MOCK)",
    "company": "Demo Company (MOCK)",
    "markers": {
        "work_mode": "hybrid",
        "location": "Москва",
        "experience_gap": "Требуется 3 года, есть ~2 — небольшой gap",
        "salary_range": "150 000 – 200 000 руб.",
        "relocation_required": False,
        "visa_sponsorship": False,
    },
    "matched_skills": ["Agile (Scrum)", "Jira", "Декомпозиция задач", "SQL", "Stakeholder Management"],
    "missing_skills": ["Salesforce CRM", "PMP сертификация"],
    "recommendation": (
        "[MOCK] Сильное совпадение по ключевым PM-компетенциям. "
        "Небольшой gap по годам опыта. Рекомендуется продолжить и адаптировать резюме."
    ),
}

_MOCK_TAILORED_RESULT = {
    "summary": (
        "[MOCK] Менеджер проектов с 2-летним опытом в IT-продуктах (финтех, FMCG). "
        "Управлял параллельными проектами с бюджетами 2М+ руб., снизил количество правок на 20% "
        "за счет выстроенных процессов коммуникации. Технический бэкграунд backend-разработчика "
        "позволяет эффективно взаимодействовать с командой разработки."
    ),
    "tailored_bullets": [
        "Управлял 3–5 параллельными IT-проектами с бюджетами 2М+ руб. → 100% соблюдение таймлайнов",
        "Снизил число правок на 20% за счёт внедрения чёткого процесса ревью с командой дизайна и разработки",
        "Ускорил прохождение задач по трекеру на 25% через приоритизацию бэклога и декомпозицию",
    ],
    "cover_letter": (
        "[MOCK] Уважаемая команда Demo Company,\n\n"
        "Меня привлекает позиция Project Manager, поскольку ваша компания работает в сфере, "
        "где я уже имею практический опыт — управление IT-проектами в условиях высоких стандартов качества. "
        "За 2 года в роли PM я управлял параллельными проектами для клиентов из финтеха и FMCG, "
        "снизил количество правок на 20% и повысил предсказуемость бюджетов на 30%.\n\n"
        "Буду рад обсудить, как мой опыт может быть полезен вашей команде.\n\n"
        "С уважением,\nПавел Коновалов"
    ),
    "changes": [
        {
            "original": "Управлял 3–5 параллельными проектами для крупных клиентов с бюджетами 2М+ руб.",
            "tailored": "Управлял 3–5 параллельными IT-проектами в сфере финтеха с бюджетами 2М+ руб. → 100% соблюдение таймлайнов",
            "reason": "Акцент на IT-проектах и финтехе, добавлены метрики результата."
        },
        {
            "original": "Настроил коммуникацию между дизайном, разработкой и заказчиком.",
            "tailored": "Внедрил систему ревью между дизайном и разработкой, что снизило количество правок на 20%.",
            "reason": "Добавлена конкретика по процессу и достигнутому результату."
        }
    ],
    "bullets_count": 3,
}


# ── Основные функции ────────────────────────────────────────────────────────

async def analyze_match(jd_text: str, applicants_count: Optional[int] = None) -> dict[str, Any]:
    """
    Сравнивает JD с master_resume.json и возвращает отчёт о совпадении.
    """
    if settings.is_mock:
        logger.info("[MOCK] analyze_match вызван в режиме заглушки")
        return _MOCK_MATCH_RESULT

    # ── Реальный вызов Gemini ──────────────────────────────────────────────
    import google.generativeai as genai

    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(settings.gemini_model)

    resume = _load_master_resume()
    prompt_template = _load_prompt("match_prompt")

    prompt = prompt_template.format(
        resume_json=json.dumps(resume, ensure_ascii=False, indent=2),
        jd_text=jd_text,
        applicants_count=applicants_count if applicants_count is not None else "Неизвестно",
    )

    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
        ),
    )

    result = json.loads(response.text)
    logger.info("Gemini analyze_match завершён, score=%.2f", result.get("score", 0))
    return result


async def generate_tailored_resume(jd_text: str, custom_note: str = "") -> dict[str, Any]:
    """
    Генерирует тейлорированное резюме и сопроводительное письмо на основе JD.
    В mock-режиме — возвращает статичный пример.
    """
    if settings.is_mock:
        logger.info("[MOCK] generate_tailored_resume вызван в режиме заглушки")
        return _MOCK_TAILORED_RESULT

    # ── Реальный вызов Gemini ──────────────────────────────────────────────
    import google.generativeai as genai

    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(settings.gemini_model)

    resume = _load_master_resume()
    prompt_template = _load_prompt("tailor_prompt")

    prompt = prompt_template.format(
        resume_json=json.dumps(resume, ensure_ascii=False, indent=2),
        jd_text=jd_text,
        custom_note=custom_note or "Нет дополнительных указаний.",
    )

    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
        ),
    )

    result = json.loads(response.text)
    logger.info(
        "Gemini tailoring завершён, пунктов переписано: %d",
        len(result.get("tailored_bullets", [])),
    )
    return result

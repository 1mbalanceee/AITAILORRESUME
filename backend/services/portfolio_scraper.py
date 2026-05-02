"""
portfolio_scraper.py — Однократный импорт данных с pkonovalov.vercel.app.

Сайт является React SPA.

Запуск:
    python backend/services/portfolio_scraper.py

Результат: обновляет секцию портфолио в master_resume.json (только проекты и summary).
"""
import asyncio
import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

PORTFOLIO_URL = "https://pkonovalov.vercel.app"
MASTER_RESUME_PATH = Path(__file__).parent.parent / "data" / "master_resume.json"


import httpx

async def scrape_portfolio() -> dict:
    """
    Загружает контент сайта через HTTP-запрос и извлекает структурированные данные.
    """
    logger.info("Загружаю портфолио %s ...", PORTFOLIO_URL)
    
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(PORTFOLIO_URL)
            response.raise_for_status()
            html = response.text
            
        # Так как сайт SPA, мы можем попробовать найти данные в HTML или 
        # просто распарсить то, что пришло (иногда SEO-версия отдает текст)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        full_text = soup.get_text(separator="\n")
        
        logger.info("Получено %d символов текста со страницы", len(full_text))
        return _parse_raw_text(full_text)
        
    except Exception as e:
        logger.error("Ошибка при скрапинге портфолио: %s", e)
        return {}


def _parse_raw_text(text: str) -> dict:
    """
    Извлекает структурированные данные из сырого текста страницы.
    Логика основана на известной структуре сайта pkonovalov.vercel.app.
    """
    result = {
        "source": PORTFOLIO_URL,
        "raw_sections": {},
        "extracted_projects": [],
        "extracted_summary": "",
    }

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    # ── Поиск саммари (первый абзац после имени) ──────────────────────────
    for i, line in enumerate(lines):
        if "Павел" in line or "Pavel" in line:
            # Берём следующие несколько строк как потенциальный summary
            candidate = " ".join(lines[i + 1 : i + 4])
            if len(candidate) > 50:
                result["extracted_summary"] = candidate
                break

    # ── Поиск проектов (строки рядом с ключевыми словами) ────────────────
    project_keywords = ["проект", "project", "запустил", "разработал", "MVP", "хакатон", "hackathon"]
    for i, line in enumerate(lines):
        if any(kw.lower() in line.lower() for kw in project_keywords):
            result["extracted_projects"].append({"raw": line, "context": lines[i + 1 : i + 3]})

    logger.info(
        "Извлечено: summary=%d chars, проектов=%d",
        len(result["extracted_summary"]),
        len(result["extracted_projects"]),
    )
    return result


def update_master_resume(scraped_data: dict) -> None:
    """
    Обновляет master_resume.json данными со скрапинга.
    Перезаписывает только поля, которые явно изменились.
    Существующие данные НЕ удаляются.
    """
    if not scraped_data:
        logger.warning("Нет данных для обновления master_resume.json")
        return

    with open(MASTER_RESUME_PATH, encoding="utf-8") as f:
        resume = json.load(f)

    changed = False

    # Обновляем summary только если скрапинг дал что-то длиннее текущего
    new_summary = scraped_data.get("extracted_summary", "")
    if new_summary and len(new_summary) > len(resume.get("summary", "")):
        logger.info("Обновляю summary из скрапинга")
        resume["summary"] = new_summary
        changed = True

    if changed:
        with open(MASTER_RESUME_PATH, "w", encoding="utf-8") as f:
            json.dump(resume, f, ensure_ascii=False, indent=2)
        logger.info("master_resume.json обновлён")
    else:
        logger.info("Изменений нет, master_resume.json не обновлён")


async def main():
    """Точка входа для ручного запуска скрапера."""
    scraped = await scrape_portfolio()

    if scraped:
        print("\n── Результат скрапинга ──")
        print(f"  Summary: {scraped.get('extracted_summary', '')[:120]}...")
        print(f"  Проектов найдено: {len(scraped.get('extracted_projects', []))}")
        update_master_resume(scraped)
    else:
        print("Скрапинг не дал результатов.")


if __name__ == "__main__":
    asyncio.run(main())

"""
jd_parser.py — Парсер описаний вакансий.
"""
import logging
import re
import asyncio
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Специфичные CSS-селекторы для популярных платформ
_SITE_SELECTORS = {
    "hh.ru": {
        "description": "[data-qa='vacancy-description'], .vacancy-description",
        "applicants": "[data-qa='vacancy-responded-count'], .vacancy-responded-count",
    },
    "linkedin.com": {
        "description": ".jobs-description__content, .description__text",
        "applicants": ".jobs-poster__status, .jobs-unified-top-card__applicant-count",
    }
}

def _clean_text(text: str) -> str:
    """Убирает лишние пробелы, переносы и мусорные символы."""
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()

def _extract_number(text: str) -> Optional[int]:
    """Извлекает число из строки (например, '142 человека' -> 142)."""
    if not text:
        return None
    match = re.search(r"(\d+)", text.replace(" ", ""))
    return int(match.group(1)) if match else None

import httpx
from bs4 import BeautifulSoup

async def fetch_jd_from_url(url: str) -> Tuple[Optional[str], Optional[int]]:
    """
    Загружает страницу вакансии через HTTP-запрос и извлекает текст.
    """
    logger.info("Загружаю вакансию: %s", url)
    
    jd_text = None
    applicants_count = None

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            html = response.text

        soup = BeautifulSoup(html, "lxml")
        
        # 1. Извлекаем описание
        selectors = _SITE_SELECTORS.get("hh.ru" if "hh.ru" in url else "generic", {})
        desc_selector = selectors.get("description", "body")
        
        # Пробуем найти по селектору
        desc_elem = soup.select_one(desc_selector)
        if desc_elem:
            jd_text = _clean_text(desc_elem.get_text(separator="\n"))
        else:
            # Fallback к body
            jd_text = _clean_text(soup.body.get_text(separator="\n") if soup.body else soup.get_text(separator="\n"))

        # 2. Извлекаем количество откликов
        app_selector = selectors.get("applicants")
        if app_selector:
            app_elem = soup.select_one(app_selector)
            if app_elem:
                applicants_count = _extract_number(app_elem.get_text())

        # 3. Поиск по тексту (если не нашли по селектору)
        if applicants_count is None:
            body_text = soup.get_text()
            patterns = [
                r"(\d+)\s+(человек|человека|людей)\s+откликнулись",
                r"(\d+)\s+(человек|человека|людей)\s+уже\s+откликнулись",
                r"откликнулись\s+(\d+)",
                r"(\d+)\s+откликов",
                r"(\d+)\s+отклик",
                r"(\d+)\s+applicants",
            ]
            for pattern in patterns:
                match = re.search(pattern, body_text, re.IGNORECASE)
                if match:
                    applicants_count = int(match.group(1))
                    break

    except Exception as e:
        logger.error("Ошибка при парсинге URL %s: %s", url, e)

    return jd_text, applicants_count

def clean_jd_text(raw_text: str) -> str:
    return _clean_text(raw_text)

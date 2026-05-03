import asyncio
import logging
import re
import json
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Application
from backend.services.gemini_service import analyze_match
from backend.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

class AggregatorService:
    def __init__(self, db: AsyncSession = None):
        self.db = db

    def _fetch_hh_vacancies(self, keywords: str, days: int = 3):
        """Fetch vacancies from HH.ru API."""
        date_from = (datetime.utcnow() - timedelta(days=days)).isoformat()
        url = "https://api.hh.ru/vacancies"
        params = {
            "text": keywords,
            "date_from": date_from,
            "per_page": 100,
            "order_by": "publication_time"
        }
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            resp.raise_for_status()
            items = resp.json().get("items", [])
            logger.info(f"HH.ru found {len(items)} vacancies for '{keywords}'")
            return [
                {
                    "title": item["name"],
                    "company": item["employer"]["name"],
                    "url": item["alternate_url"],
                    "source": "hh.ru",
                    "id": item["id"]
                }
                for item in items
            ]
        except Exception as e:
            logger.error(f"Error fetching from HH.ru: {e}")
            return []

    def _fetch_habr_vacancies(self, keywords: str):
        """Fetch vacancies from Habr Career RSS."""
        # Habr doesn't have a reliable date_from in RSS query, so we'll fetch recent ones
        url = f"https://career.habr.com/vacancies/rss?q={keywords}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, "xml")
            items = soup.find_all("item")
            logger.info(f"Habr Career found {len(items)} vacancies for '{keywords}'")
            return [
                {
                    "title": item.title.text,
                    "company": item.author.text if item.author else "Unknown",
                    "url": item.link.text,
                    "source": "habr_career",
                    "id": item.guid.text if item.guid else item.link.text
                }
                for item in items
            ]
        except Exception as e:
            logger.error(f"Error fetching from Habr Career: {e}")
            return []

    async def _get_vacancy_text(self, url: str, source: str, hh_id: str = None):
        """Extract full JD text from source."""
        if source == "hh.ru" and hh_id:
            try:
                # Use HH.ru API for clean JD
                api_url = f"https://api.hh.ru/vacancies/{hh_id}"
                resp = requests.get(api_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                return BeautifulSoup(data["description"], "lxml").get_text(separator="\n")
            except:
                pass
        
        # Fallback to simple scraping or return placeholder
        try:
            resp = requests.get(url, headers={"User-Agent": "AI-Tailor-App/1.0"}, timeout=5)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, "lxml")
            # Remove scripts and styles
            for s in soup(["script", "style"]):
                s.extract()
            return soup.get_text(separator="\n", strip=True)[:5000]
        except Exception as e:
            logger.warning(f"Could not fetch JD text from {url}: {e}")
            return "Описание вакансии не удалось загрузить автоматически."

    async def run_discovery(self, keywords_list: list[str], days: int = 3):
        """
        Main loop: Discover, Filter, Analyze, Save.
        """
        all_found = []
        for kw in keywords_list:
            all_found.extend(self._fetch_hh_vacancies(kw, days))
            all_found.extend(self._fetch_habr_vacancies(kw))

        # Deduplicate by URL
        unique_vacancies = {v["url"]: v for v in all_found}.values()
        
        # STRICT TITLE MATCH
        # Filter by regex: any of the keywords should be in the title
        kw_regex = re.compile(r"|".join(map(re.escape, keywords_list)), re.IGNORECASE)
        filtered = [v for v in unique_vacancies if kw_regex.search(v["title"])]
        
        # LIMIT for faster results and to avoid 'infinite' feeling
        filtered = filtered[:15] 
        logger.info(f"Aggregator: Analyzing {len(filtered)} vacancies...")

        new_scored_count = 0
        async with AsyncSessionLocal() as db:
            for i, v in enumerate(filtered):
                logger.info(f"Aggregator: Analyzing [{i+1}/{len(filtered)}] {v['title']} at {v['company']}")
                # 1. Check if URL already exists
                stmt = select(Application).where(Application.job_url == v["url"])
                existing = await db.execute(stmt)
                if existing.scalar_one_or_none():
                    logger.info(f"Aggregator: Already exists, skipping.")
                    continue

                # 2. If new: Fetch full text
                jd_text = await self._get_vacancy_text(v["url"], v["source"], v.get("id") if v["source"] == "hh.ru" else None)
                
                # 3. Call Gemini
                try:
                    analysis = await analyze_match(jd_text)
                    
                    # 4. Save to DB
                    new_app = Application(
                        job_title=v["title"],
                        company=v["company"],
                        job_url=v["url"],
                        jd_raw=jd_text,
                        match_score=analysis.get("score", 0.0),
                        match_report=json.dumps(analysis, ensure_ascii=False),
                        work_mode=analysis.get("markers", {}).get("work_mode", "N/A"),
                        experience_gap=analysis.get("markers", {}).get("experience_gap"),
                        salary_range=analysis.get("markers", {}).get("salary_range"),
                        is_analyzed=True,
                        kanban_status=None,
                        status="analyzed"
                    )
                    db.add(new_app)
                    new_scored_count += 1
                    logger.info(f"Aggregator: Scored {v['title']} - {new_app.match_score*100}%")
                    
                    # Prevent rate limiting and heavy load
                    await asyncio.sleep(0.5) 
                except Exception as e:
                    logger.error(f"Failed to analyze vacancy {v['url']}: {e}")

            await db.commit()
        
        return new_scored_count

aggregator = AggregatorService()

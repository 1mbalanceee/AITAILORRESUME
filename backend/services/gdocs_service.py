"""
gdocs_service.py — Интеграция с Google Docs API (OAuth 2.0 User Flow).

Логика замены контента:
  1. Клонируем шаблон.
  2. Заменяем Summary (Обо мне).
  3. Заменяем Skills (Навыки).
  4. Заменяем Bullets в опыте работы (используем маркеры должностей).
  5. Сопроводительное письмо НЕ добавляется в документ (хранится отдельно).
"""
import os
import logging
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from backend.config import settings

logger = logging.getLogger(__name__)

# МАРКЕРЫ ДЛЯ ЗАМЕНЫ (должны точно соответствовать тексту в вашем шаблоне)
_MARKERS = {
    "summary": "Синхронизирую креативные идеи с технической реализацией: от брифа и оценки маржинальности до запуска спецпроектов и поддержки брендов.",
    "skills": "Management: Agile (Scrum/Kanban), Управление рисками, Декомпозиция, Сбор требований.\nTechnical: API/Интеграции, SQL, CI/CD (баз.), Backend patterns.\nTools: Jira, Yandex Tracker, Notion, Miro, GitHub",
    "exp_bullets_1": "• Руководил кросс-функциональной командой из 10 человек (разработчики, дизайнеры, менеджеры).\n• Спроектировал и запустил систему автоматизации отчетности, сократив время обработки данных на 40%.",
}

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
]

def _get_credentials():
    creds = None
    if os.path.exists(settings.google_token_path):
        creds = Credentials.from_authorized_user_file(settings.google_token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(settings.google_credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(settings.google_token_path, "w") as token:
            token.write(creds.to_json())
    return creds

def _make_replace_request(old_text: str, new_text: str) -> dict:
    return {
        "replaceAllText": {
            "containsText": {"text": old_text, "matchCase": True},
            "replaceText": new_text,
        }
    }

async def create_resume_doc(
    tailored_data: dict,
    resume_data: dict,
    job_title: str,
) -> Optional[str]:
    if settings.is_mock:
        return "https://docs.google.com/document/d/MOCK_DOC_ID/edit"

    import asyncio
    from functools import partial

    loop = asyncio.get_event_loop()
    creds = await loop.run_in_executor(None, _get_credentials)
    
    docs_service = build("docs", "v1", credentials=creds, static_discovery=False)
    drive_service = build("drive", "v3", credentials=creds, static_discovery=False)

    personal = resume_data.get("personal", {})
    doc_title = f"CV — {personal.get('name', 'Павел Коновалов')} — {job_title}"
    
    clone_func = partial(drive_service.files().copy(fileId=settings.gdoc_template_id, body={"name": doc_title}).execute)
    copied_file = await loop.run_in_executor(None, clone_func)
    new_doc_id = copied_file["id"]

    # ─── Подготовка контента ───
    new_summary = tailored_data.get("summary", _MARKERS["summary"])
    
    # Сбор навыков
    selected_skills = tailored_data.get("selected_skills", [])
    if not selected_skills:
        new_skills = _MARKERS["skills"]
    else:
        new_skills = (
            f"Management: {', '.join(selected_skills[:5])}\n"
            f"Technical: {', '.join(selected_skills[5:8])}\n"
            f"Tools: Jira, Yandex Tracker, Notion, Miro, GitHub"
        )

    # Опыт работы (Буллеты)
    # Gemini возвращает tailored_bullets: list[str]
    tailored_bullets_list = tailored_data.get("tailored_bullets", [])
    if tailored_bullets_list:
        new_bullets_text = "\n".join([f"• {b}" for b in tailored_bullets_list[:3]])
    else:
        new_bullets_text = _MARKERS["exp_bullets_1"]

    batch_requests = [
        _make_replace_request(_MARKERS["summary"], new_summary),
        _make_replace_request(_MARKERS["skills"], new_skills),
        _make_replace_request(_MARKERS["exp_bullets_1"], new_bullets_text),
    ]

    # Выполняем замены
    update_func = partial(docs_service.documents().batchUpdate(documentId=new_doc_id, body={"requests": batch_requests}).execute)
    await loop.run_in_executor(None, update_func)
    
    # ─── Sharing Permissions (Anyone with link can view) ───
    share_func = partial(
        drive_service.permissions().create(
            fileId=new_doc_id,
            body={"type": "anyone", "role": "reader"},
        ).execute
    )
    await loop.run_in_executor(None, share_func)

    return f"https://docs.google.com/document/d/{new_doc_id}/edit"

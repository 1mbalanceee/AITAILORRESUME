"""
config.py — Настройки приложения через pydantic-settings.
Значения читаются из .env файла автоматически.
"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

# Ищем .env в текущей папке или в родительской (когда запускаем из backend/)
_env_candidates = [Path(".env"), Path("../.env")]
_env_file = next((str(p) for p in _env_candidates if p.exists()), ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_file,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Gemini
    gemini_api_key: str = "NOT_SET"
    gemini_model: str = "gemini-1.5-pro-latest"

    # Google Docs (OAuth 2.0 User Flow)
    google_credentials_path: str = "./backend/client_secret.json"
    google_token_path: str = "./backend/token.json"
    gdoc_template_id: str = "1A0Iv8sVOXVj_cnKChDZtYfFBCJFetD6Yn9AfeXfPCGo"

    # Database
    database_url: str = "sqlite+aiosqlite:///./backend/data/applications.db"

    # App
    # "mock" — возвращает заглушки без вызова реального API
    # "live" — использует настоящий Gemini API
    app_mode: str = "mock"
    debug: bool = True
    cors_origins: List[str] = ["http://localhost:5173"]

    @property
    def is_mock(self) -> bool:
        return self.app_mode == "mock"


settings = Settings()

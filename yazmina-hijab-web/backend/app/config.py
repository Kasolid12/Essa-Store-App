"""
Yazmina Hijab Web — Application Configuration.
All secrets and env-dependent values live here, loaded from .env.
"""

import os
from functools import lru_cache

from pydantic_settings import BaseSettings


# Path to backend/.env (absolute, regardless of CWD)
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ENV_PATH = os.path.join(_BACKEND_DIR, ".env")


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///yazmina_web.db"

    # ── Auth / JWT ────────────────────────────────────────────────────
    SECRET_KEY: str = "CHANGE-ME-to-a-random-64-char-string"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 12

    # ── App ───────────────────────────────────────────────────────────
    APP_NAME: str = "Yazmina Hijab"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # CORS — frontend dev server
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    model_config = {
        "env_file": _ENV_PATH,
        "env_file_encoding": "utf-8",
        "extra": "ignore",  # Ignore extra env vars (e.g. from parent project's .env)
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()

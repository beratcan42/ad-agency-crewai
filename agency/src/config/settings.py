"""Uygulama yapılandırması — Pydantic Settings ile .env'i okur."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    PROJECT_NAME: str = "ad-agency"
    ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    TZ: str = "Europe/Istanbul"

    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "agency"
    POSTGRES_USER: str = "agency"
    POSTGRES_PASSWORD: str = Field(default="")
    DATABASE_URL: str = Field(default="")

    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = Field(default="")
    REDIS_URL: str = Field(default="")
    CELERY_BROKER_URL: str = Field(default="")
    CELERY_RESULT_BACKEND: str = Field(default="")

    OPENROUTER_API_KEY: str = Field(default="")
    GOOGLE_GEMINI_API_KEY: str = Field(default="")
    HUGGINGFACE_TOKEN: str = Field(default="")

    OLLAMA_URL: str = "http://host.docker.internal:11434"
    OLLAMA_DEFAULT_MODEL: str = "qwen3.5:9b"

    VAULT_BASE_PATH: str = "/vaults"

    AGENCY_API_HOST: str = "0.0.0.0"
    AGENCY_API_PORT: int = 8000
    UVICORN_WORKERS: int = 3

    CREW_MAX_ITER: int = 10
    CREW_MAX_EXECUTION_TIME: int = 300
    CREW_MAX_RPM: int = 20
    TOKEN_BUDGET_PER_CAMPAIGN: int = 100_000
    TOKEN_BUDGET_DAILY_GLOBAL: int = 500_000
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 3
    CIRCUIT_BREAKER_TIMEOUT_SEC: int = 300

    @property
    def app_root(self) -> Path:
        return Path(__file__).resolve().parents[2]

    @property
    def models_yaml_path(self) -> Path:
        return Path(__file__).resolve().parent / "models.yaml"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

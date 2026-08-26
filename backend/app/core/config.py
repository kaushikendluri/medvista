"""Application configuration, read entirely from environment variables.

Never hardcode secrets or connection strings here — this module only defines
the shape of configuration and safe local-dev defaults for non-secret values.
"""
from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Core
    ENVIRONMENT: str = "development"
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+psycopg://medvista:medvista@localhost:5432/medvista"
    )

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Auth
    AUTH_SECRET: str = Field(default="INSECURE-DEV-SECRET-CHANGE-ME")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12
    JWT_ALGORITHM: str = "HS256"

    # DICOM server (Orthanc) — used from Phase 2 onward
    DICOM_SERVER_URL: str = "http://localhost:8042"
    DICOM_SERVER_USERNAME: str = "orthanc"
    DICOM_SERVER_PASSWORD: str = "orthanc"

    # Object storage — used from Phase 2 onward
    OBJECT_STORAGE_ENDPOINT: str = ""
    OBJECT_STORAGE_ACCESS_KEY: str = ""
    OBJECT_STORAGE_SECRET_KEY: str = ""
    OBJECT_STORAGE_BUCKET: str = "medvista-imaging"

    # AI / LLM providers — abstraction wired from Phase 4/6 onward.
    # Absence of a key means the corresponding capability reports itself
    # as unavailable; it must never be simulated.
    AI_PROVIDER: str = ""
    AI_MODEL: str = ""
    LLM_PROVIDER: str = ""
    LLM_API_KEY: str = ""

    # Feature flags
    ENABLE_3D: bool = False
    ENABLE_AI: bool = False
    ENABLE_VOICE: bool = False
    ENABLE_COPILOT: bool = False
    ENABLE_RESEARCH_MODE: bool = False
    ENABLE_COLLABORATION: bool = False

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from pathlib import Path

class Settings(BaseSettings):
    APP_ENV: str = "development"
    DATABASE_URL: str = "sqlite:///./database/company_duplicates.db"
    FUZZY_THRESHOLD: float = 80.0
    MATCHING_ALGORITHM: str = "rapidfuzz_ratio"
    AI_VERIFICATION_ENABLED: bool = False
    SEARCH_PROVIDER: str = "none"
    LLM_PROVIDER: str = "none"
    MAX_UPLOAD_SIZE_MB: int = 5
    MAX_AI_CANDIDATES_PER_RUN: int = 20
    MAX_AI_COST_PER_RUN_USD: float = 1.0
    MAX_AI_DAILY_COST_USD: float = 5.0
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

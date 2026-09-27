from datetime import date

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str

    @field_validator("database_url")
    @classmethod
    def use_psycopg_driver(cls, url: str) -> str:
        """Tiger Data hands out postgres:// URLs, which SQLAlchemy does not accept as they are."""
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url[len(prefix):]
        return url

    # Classification thresholds (see docs/requirements.md, section A).
    group_confidence_threshold: float = 0.6  # stage 1 top probability below this falls back to the data category
    flag_threshold: float = 0.5  # text flag fires at or above this probability
    emergency_threshold: float = 0.5

    preload_laya: bool = True  # load the model when the server starts, not on the first request

    # The data runs to 2026-09-30, so "days open" is measured from this date, not today. Falls back to
    # app_settings.as_of_date in the database, then to today.
    as_of_date: date | None = None

    # Domain AI agents (see app/agents/). agent_model is a placeholder tag until the team confirms
    # which local Ollama model they're running (`ollama pull <model>` first).
    agent_enabled: bool = True  # False uses the template fallback everywhere (requirement N6)
    agent_model: str = "gemma3"
    ollama_host: str = "http://localhost:11434"


settings = Settings()

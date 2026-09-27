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

    # Domain AI agents (see app/agents/). gemma3 has no tool-calling support in Ollama at all;
    # gemma4 does (native, ~86% tool-calling accuracy per Google). Run `ollama pull gemma4` first.
    agent_enabled: bool = True  # False turns off AI chat everywhere (requirement N6)
    agent_model: str = "gemma4:e4b-it-qat"  # small gemma4 build (6 GB); runs on the Mac GPU via Ollama
    ollama_host: str = "http://localhost:11434"
    agent_timeout_seconds: float = 30.0  # per Ollama call


settings = Settings()

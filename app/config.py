from datetime import date

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str

    # Classification thresholds (see docs/requirements.md, section A).
    group_confidence_threshold: float = 0.6  # stage 1 top probability below this goes to a person
    flag_threshold: float = 0.5  # text flag fires at or above this probability
    emergency_threshold: float = 0.5

    preload_laya: bool = True  # load the model when the server starts, not on the first request

    # The data runs to 2026-09-30, so "days open" is measured from this date, not today.
    as_of_date: date | None = None


settings = Settings()

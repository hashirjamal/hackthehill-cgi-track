from datetime import date

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.classification.service import db_as_of_date
from app.config import Settings


def test_tiger_data_urls_are_rewritten_for_sqlalchemy():
    tail = "tsdbadmin:pw@host.tsdb.cloud.timescale.com:31279/tsdb?sslmode=require"
    for scheme in ("postgres://", "postgresql://", "postgresql+psycopg://"):
        assert Settings(database_url=scheme + tail).database_url == "postgresql+psycopg://" + tail
    assert Settings(database_url="sqlite:///./dev.db").database_url == "sqlite:///./dev.db"


def test_as_of_date_comes_from_app_settings_when_the_table_exists():
    engine = create_engine("sqlite://")
    with Session(engine) as db:
        assert db_as_of_date(db) is None  # no table, as on the local SQLite database

        db.execute(text("CREATE TABLE app_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)"))
        assert db_as_of_date(db) is None  # table but no row

        db.execute(text("INSERT INTO app_settings VALUES ('as_of_date', '2026-09-30')"))
        assert db_as_of_date(db) == date(2026, 9, 30)


def test_agent_settings_have_working_defaults():
    from app.config import Settings

    s = Settings(database_url="sqlite:///./dev.db")
    assert s.agent_enabled is True
    assert s.agent_model == "gemma3"
    assert s.ollama_host == "http://localhost:11434"

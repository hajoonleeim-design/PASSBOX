from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = ""
    jwt_secret_key: str = ""
    storage_root: str = "storage"
    gateway_mode: str = "MOCK"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    jwt_access_token_minutes: int = 60
    login_rate_limit_attempts: int = 5
    login_rate_limit_window_seconds: int = 60
    cors_allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class Base(DeclarativeBase):
    pass


def get_engine():
    settings = Settings()
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not configured")

    return create_engine(settings.database_url, pool_pre_ping=True)


def get_session_factory():
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)


def check_database() -> None:
    engine = get_engine()
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    engine.dispose()

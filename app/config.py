"""Application configuration from environment variables."""
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    APP_NAME: str = "BilimAI"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    SECRET_KEY: str = "dev-insecure-secret-change-me-please-32chars"
    SESSION_COOKIE_NAME: str = "bilimai_session"
    SESSION_MAX_AGE: int = 604800

    DATABASE_URL: str = "sqlite:///./bilimai.db"

    AI_PROVIDER: str = "groq"
    AI_API_KEY: str = ""
    AI_BASE_URL: str = "https://api.groq.com/openai/v1"
    AI_MODEL: str = "openai/gpt-oss-120b"
    AI_TIMEOUT: int = 60

    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "12admin"
    ADMIN_EMAIL: str = "admin@bilimai.local"

    BCRYPT_ROUNDS: int = 12
    RATE_LIMIT_PER_MINUTE: int = 60

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"

    @property
    def database_url_normalized(self) -> str:
        """Render/Heroku gives postgres:// — SQLAlchemy needs postgresql://"""
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

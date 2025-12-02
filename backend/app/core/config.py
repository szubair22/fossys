"""
Application configuration settings.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # Application
    APP_ENV: str = "development"
    DEBUG: bool = True
    APP_NAME: str = "OrgSuite API"
    API_V1_PREFIX: str = "/api"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://orgmeet:orgmeet@orgmeet-db:5432/orgmeet"
    DATABASE_URL_SYNC: str = "postgresql://orgmeet:orgmeet@orgmeet-db:5432/orgmeet"

    # JWT Authentication
    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # File uploads
    UPLOAD_DIR: str = "/app/uploads"
    MAX_UPLOAD_SIZE: int = 52428800  # 50MB

    # SMTP (for email notifications)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 465
    SMTP_TLS: bool = True
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_SENDER: str = "noreply@orgmeet.local"

    # Jitsi
    JITSI_DOMAIN: str = "meet.jit.si"

    # Site URL
    SITE_URL: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

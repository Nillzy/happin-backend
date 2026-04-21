"""Application configuration and settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Supabase Configuration
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_JWT_SECRET: str | None = None
    DATABASE_URL: str | None = None

    # Application Settings
    DEBUG: bool = False
    LOG_LEVEL: str = "info"

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()

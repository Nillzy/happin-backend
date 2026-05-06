"""Application configuration and settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    # Supabase Configuration
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str | None = None
    SUPABASE_JWT_SECRET: str | None = None
    DATABASE_URL: str | None = None

    # Application Settings
    DEBUG: bool = False
    LOG_LEVEL: str = "info"

    # MapTiler Geocoding
    MAPTILER_KEY: str | None = None

    # Unsplash API
    UNSPLASH_ACCESS_KEY: str | None = None


# Global settings instance
settings = Settings()

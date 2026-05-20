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

    # Ticket HMAC signing
    TICKET_SIGNING_KEY: str = ""

    # Stripe Connect
    STRIPE_SECRET_KEY: str | None = None
    STRIPE_WEBHOOK_SECRET: str | None = None
    PLATFORM_FEE_BPS: int = 500  # 5% default
    STRIPE_CHECKOUT_SUCCESS_URL: str = ""
    STRIPE_CHECKOUT_CANCEL_URL: str = ""
    STRIPE_CONNECT_REFRESH_URL: str = "https://happin.fun/connect/refresh"
    STRIPE_CONNECT_RETURN_URL: str = "https://happin.fun/connect/return"

    # Google Wallet
    GOOGLE_WALLET_ISSUER_ID: str | None = None
    GOOGLE_SERVICE_ACCOUNT_FILE: str | None = None


# Global settings instance
settings = Settings()

"""Supabase client initialization."""

from supabase import create_client, Client
from app.core.config import settings

# Lazy initialization - only create client when accessed
_supabase_client: Client | None = None


def get_supabase() -> Client:
    """
    Get or create Supabase client.

    Lazy initialization prevents crashes on startup if Supabase is not available.
    """
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(
            supabase_url=settings.SUPABASE_URL,
            supabase_key=settings.SUPABASE_ANON_KEY
        )
    return _supabase_client


# For backwards compatibility
supabase = get_supabase()

"""Supabase client initialization."""

from supabase import create_client, Client
from supabase.lib.client_options import SyncClientOptions as ClientOptions
from app.core.config import settings

# Lazy initialization - only create client when accessed
_supabase_client: Client | None = None
_supabase_admin_client: Client | None = None


def get_supabase() -> Client:
    """
    Get or create the default Supabase client (anon key).

    Used for read-only public queries (GET endpoints).
    """
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(
            supabase_url=settings.SUPABASE_URL,
            supabase_key=settings.SUPABASE_ANON_KEY
        )
    return _supabase_client


def get_supabase_admin() -> Client:
    """
    Get or create a Supabase client with the service role key.

    Bypasses RLS — use only for operations where authorization
    has already been verified at the API layer.
    """
    global _supabase_admin_client
    if _supabase_admin_client is None:
        key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY
        _supabase_admin_client = create_client(
            supabase_url=settings.SUPABASE_URL,
            supabase_key=key
        )
    return _supabase_admin_client


def get_supabase_for_user(token: str) -> Client:
    """
    Create a Supabase client authenticated as a specific user.

    The user's JWT is set as the Authorization header, so PostgREST
    applies RLS policies for the 'authenticated' role.
    """
    return create_client(
        supabase_url=settings.SUPABASE_URL,
        supabase_key=settings.SUPABASE_ANON_KEY,
        options=ClientOptions(
            headers={"Authorization": f"Bearer {token}"}
        )
    )


# For backwards compatibility
supabase = get_supabase()

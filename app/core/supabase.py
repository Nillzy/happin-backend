"""Supabase client initialization."""

from supabase import create_client, Client
from app.core.config import settings

# Initialize Supabase client
supabase: Client = create_client(
    supabase_url=settings.SUPABASE_URL,
    supabase_key=settings.SUPABASE_KEY
)

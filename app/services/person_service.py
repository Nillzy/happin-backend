"""Person-related business logic — links Supabase Auth users to person records."""

from app.core.supabase import get_supabase_for_user


def get_or_create_person(supabase_user_id: str, email: str | None, token: str) -> dict:
    supabase = get_supabase_for_user(token)

    response = (
        supabase.table("person")
        .select("*")
        .eq("supabase_user_id", supabase_user_id)
        .maybe_single()
        .execute()
    )

    if response and response.data:
        return response.data

    first_name = (email.split("@")[0] if email else "User")

    new_person = (
        supabase.table("person")
        .insert({
            "supabase_user_id": supabase_user_id,
            "email_address": email,
            "first_name": first_name,
        })
        .execute()
    )

    return new_person.data[0]

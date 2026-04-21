"""User endpoints for profile and account management."""

from fastapi import APIRouter, Depends
from app.core.auth import get_current_user
from app.schemas.user import UserResponse

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(user=Depends(get_current_user)):
    """
    Get current authenticated user information.

    This endpoint is useful for:
    - Testing the full authentication flow
    - Getting user profile data
    - Verifying JWT tokens

    Returns:
        UserResponse with user id, phone, email, etc.
    """
    # user object comes from Supabase Auth via get_current_user dependency
    return UserResponse(
        id=user.user.id,
        phone=user.user.phone,
        email=user.user.email,
        created_at=user.user.created_at,
    )

"""Authentication middleware and dependencies."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from app.core.supabase import supabase

# HTTP Bearer token scheme
security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthCredentials = Depends(security)):
    """
    Validate JWT token and return current user.

    This dependency validates the JWT token from the Authorization header
    against Supabase Auth and returns the authenticated user.

    Args:
        credentials: HTTP Bearer credentials from request header

    Returns:
        User object from Supabase Auth

    Raises:
        HTTPException: 401 if token is invalid or expired
    """
    token = credentials.credentials

    try:
        # Validate JWT with Supabase
        user = supabase.auth.get_user(token)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_optional(
    credentials: HTTPAuthCredentials | None = Depends(HTTPBearer(auto_error=False))
):
    """
    Optional authentication - returns user if authenticated, None otherwise.

    Useful for endpoints that work differently for authenticated vs anonymous users
    (e.g., public event list shows more details for authenticated users).

    Args:
        credentials: Optional HTTP Bearer credentials

    Returns:
        User object if authenticated, None otherwise
    """
    if not credentials:
        return None

    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None

"""API v1 main router - aggregates all sub-routers."""

from fastapi import APIRouter
from app.api.v1 import user, events, ticket_options

# Create main v1 router
router = APIRouter(prefix="/api/v1")

# Include user router (for testing auth flow)
router.include_router(user.router, prefix="/user", tags=["user"])

# Include events router (public event listing and detail)
router.include_router(events.router, prefix="/events", tags=["events"])

# Include ticket options router (nested under events)
router.include_router(ticket_options.router, prefix="/events", tags=["ticket-options"])


@router.get("/health")
async def health_check():
    """API v1 health check endpoint."""
    return {"status": "healthy", "version": "v1"}

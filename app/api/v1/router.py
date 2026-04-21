"""API v1 main router - aggregates all sub-routers."""

from fastapi import APIRouter
from app.api.v1 import user

# Create main v1 router
router = APIRouter(prefix="/api/v1")

# Include user router (for testing auth flow)
router.include_router(user.router, prefix="/user", tags=["user"])

# TODO: Import and include more sub-routers as they are created
# Example:
# from app.api.v1 import events, rsvp, tickets
# router.include_router(events.router, prefix="/events", tags=["events"])
# router.include_router(rsvp.router, prefix="/rsvp", tags=["rsvp"])
# router.include_router(tickets.router, prefix="/tickets", tags=["tickets"])


@router.get("/health")
async def health_check():
    """API v1 health check endpoint."""
    return {"status": "healthy", "version": "v1"}

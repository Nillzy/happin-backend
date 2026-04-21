"""FastAPI application entry point."""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import router as api_v1_router
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Happin Backend API",
    description="Backend API for Happin Event Discovery Platform",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,  # Disable docs in production
    redoc_url="/redoc" if settings.DEBUG else None,
    debug=settings.DEBUG,
)

# CORS Configuration
# TODO: Configure allowed origins based on environment in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure specific origins for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint - API information."""
    return {
        "message": "Happin Backend API",
        "version": "1.0.0",
        "docs": "/docs" if settings.DEBUG else "disabled",
        "health": "/health",
    }


@app.get("/health")
async def health():
    """Health check endpoint for monitoring and load balancers."""
    return {
        "status": "healthy",
        "version": "1.0.0",
    }


# Include API v1 router
app.include_router(api_v1_router)


@app.on_event("startup")
async def startup_event():
    """Application startup event handler."""
    logger.info("Starting Happin Backend API")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info(f"Supabase URL: {settings.SUPABASE_URL}")
    logger.info("Application startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event handler."""
    logger.info("Shutting down Happin Backend API")


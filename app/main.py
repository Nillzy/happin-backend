"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import router as api_v1_router
from app.core.config import settings

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Happin Backend API")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info(f"Supabase URL: {settings.SUPABASE_URL}")
    logger.info("Application startup complete")
    yield
    logger.info("Shutting down Happin Backend API")


app = FastAPI(
    title="Happin Backend API",
    description="Backend API for Happin Event Discovery Platform",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# CORS Configuration
# TODO: Configure allowed origins based on environment in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
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


app.include_router(api_v1_router)


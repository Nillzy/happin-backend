"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.v1.router import router as api_v1_router
from app.core.config import settings
from app.services.reminder_scheduler import start_scheduler, stop_scheduler

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
    start_scheduler()
    logger.info("Application startup complete")
    yield
    stop_scheduler()
    logger.info("Shutting down Happin Backend API")


app = FastAPI(
    title="Happin Backend API",
    description="Backend API for Happin Event Discovery Platform",
    version="1.0.0",
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# CORS Configuration
# TODO: Configure allowed origins based on environment in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure specific origins for production
    allow_credentials=False,  # JWT via Authorization header, not cookies
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint - API information."""
    return {
        "message": "Happin Backend API",
        "version": "1.0.0",
        "docs": "/api/docs" if settings.DEBUG else "disabled",
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

static_dir = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

docs_dir = Path(__file__).resolve().parent.parent / "site"
if settings.DEBUG and docs_dir.exists():
    app.mount("/docs", StaticFiles(directory=docs_dir, html=True), name="docs")


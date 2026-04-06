"""
FastAPI application — entry point for the Slide Deck Generator backend.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router, ws_router
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-30s | %(levelname)-7s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle hook."""
    # Ensure data directories exist
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.GENERATED_DIR).mkdir(parents=True, exist_ok=True)
    logger.info("Upload dir:    %s", Path(settings.UPLOAD_DIR).resolve())
    logger.info("Generated dir: %s", Path(settings.GENERATED_DIR).resolve())
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="Slide Deck Generator",
    description="Automated quarterly client meeting PowerPoint generator",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow all origins for prototype
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(api_router)
app.include_router(ws_router)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "slide-deck-generator",
        "version": "0.1.0",
    }

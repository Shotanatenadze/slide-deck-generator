"""Aggregate all sub-routers."""

from fastapi import APIRouter

from app.api import upload, generate, download, ws

api_router = APIRouter(prefix="/api")
api_router.include_router(upload.router, tags=["upload"])
api_router.include_router(generate.router, tags=["generate"])
api_router.include_router(download.router, tags=["download"])

# WebSocket lives at /ws, not /api
ws_router = ws.router

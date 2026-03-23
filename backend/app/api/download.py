"""Download endpoint — serves generated .pptx files."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.storage.local import find_generated_deck

router = APIRouter()


@router.get("/download/{generation_id}")
async def download_deck(generation_id: str):
    """
    Download the generated PowerPoint deck for a given generation.

    Returns the .pptx file as a downloadable attachment.
    """
    deck_path = find_generated_deck(generation_id)
    if not deck_path:
        raise HTTPException(
            status_code=404,
            detail=f"No generated deck found for generation_id={generation_id}",
        )

    path = Path(deck_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Deck file not found on disk")

    return FileResponse(
        path=str(path),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=path.name,
    )

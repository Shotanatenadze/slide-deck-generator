"""Upload endpoint — receives Excel and PDF files for a generation."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.models.schemas import FileInfo, UploadResponse
from app.storage.local import save_upload

router = APIRouter()

ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".pdf"}


@router.post("/upload", response_model=UploadResponse)
async def upload_files(
    files: List[UploadFile] = File(...),
    generation_id: Optional[str] = Form(default=None),
):
    """
    Upload one or more Excel or PDF files for deck generation.

    If no generation_id is provided, a new one is created.
    Returns the generation_id and metadata about saved files.
    """
    gen_id = generation_id or uuid.uuid4().hex

    saved: List[FileInfo] = []
    for f in files:
        ext = Path(f.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {ext}. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
            )
        content = await f.read()
        path = save_upload(gen_id, f.filename, content)
        saved.append(FileInfo(
            filename=f.filename,
            size=len(content),
            path=path,
        ))

    return UploadResponse(generation_id=gen_id, files=saved)

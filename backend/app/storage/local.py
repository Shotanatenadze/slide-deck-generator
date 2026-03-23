"""
Local filesystem storage for uploads and generated decks.

In production this would be replaced by an object-store adapter (S3, Azure Blob, GCS).
"""

from __future__ import annotations

import shutil
from pathlib import Path

from app.config import settings


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Uploads
# ---------------------------------------------------------------------------

def save_upload(generation_id: str, filename: str, content: bytes) -> str:
    """
    Persist an uploaded file to disk.

    Returns the absolute path to the saved file.
    """
    dest_dir = Path(settings.UPLOAD_DIR) / generation_id
    _ensure_dir(dest_dir)
    dest = dest_dir / filename
    dest.write_bytes(content)
    return str(dest.resolve())


def get_upload_path(generation_id: str, filename: str) -> str:
    """Return the absolute path where an upload *would* be stored."""
    return str((Path(settings.UPLOAD_DIR) / generation_id / filename).resolve())


def list_uploads(generation_id: str) -> list[str]:
    """Return list of absolute paths for all files uploaded under this generation."""
    upload_dir = Path(settings.UPLOAD_DIR) / generation_id
    if not upload_dir.exists():
        return []
    return [str(f.resolve()) for f in upload_dir.iterdir() if f.is_file()]


# ---------------------------------------------------------------------------
# Generated artifacts
# ---------------------------------------------------------------------------

def save_generated(generation_id: str, filename: str, source_path: str) -> str:
    """
    Copy or save a generated file into the generated artifacts directory.

    If *source_path* points to an existing file it will be copied.
    Returns the absolute destination path.
    """
    dest_dir = Path(settings.GENERATED_DIR) / generation_id
    _ensure_dir(dest_dir)
    dest = dest_dir / filename

    src = Path(source_path)
    if src.exists() and src.is_file():
        shutil.copy2(str(src), str(dest))
    else:
        # source_path might already be in the right place
        # (pptx_builder writes directly to GENERATED_DIR)
        pass

    return str(dest.resolve())


def get_generated_path(generation_id: str, filename: str) -> str:
    return str((Path(settings.GENERATED_DIR) / generation_id / filename).resolve())


def find_generated_deck(generation_id: str) -> str | None:
    """Find the first .pptx file in the generated directory for this generation."""
    gen_dir = Path(settings.GENERATED_DIR) / generation_id
    if not gen_dir.exists():
        return None
    pptx_files = list(gen_dir.glob("*.pptx"))
    if pptx_files:
        return str(pptx_files[0].resolve())
    return None

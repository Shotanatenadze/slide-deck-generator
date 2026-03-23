"""Generate endpoint — triggers deck generation pipeline."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

from app.agents.orchestrator import OrchestratorAgent
from app.models.schemas import GenerationRequest
from app.storage.local import list_uploads

router = APIRouter()


@router.post("/generate")
async def generate_deck(request: GenerationRequest):
    """
    Start asynchronous deck generation.

    Expects a GenerationRequest with the generation_id from a prior upload,
    along with client metadata and optional analyst prompt / market context.

    Returns immediately with status "generating". Progress is streamed via
    the WebSocket at /ws/generation/{generation_id}.
    """
    # Validate that files have been uploaded for this generation
    uploaded = list_uploads(request.generation_id)
    if not uploaded:
        raise HTTPException(
            status_code=400,
            detail=f"No uploaded files found for generation_id={request.generation_id}. "
                   "Upload files first via POST /api/upload.",
        )

    # Launch orchestrator as a background task
    orchestrator = OrchestratorAgent(request.generation_id)

    asyncio.create_task(
        orchestrator.run(
            generation_id=request.generation_id,
            client_name=request.client_name,
            analyst_prompt=request.analyst_prompt,
            market_context=request.market_context,
        )
    )

    return {
        "generation_id": request.generation_id,
        "status": "generating",
    }

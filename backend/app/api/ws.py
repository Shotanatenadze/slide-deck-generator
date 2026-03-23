"""WebSocket endpoint — streams agent events to the client."""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.agents import event_bus

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/generation/{generation_id}")
async def generation_ws(websocket: WebSocket, generation_id: str):
    """
    WebSocket that streams AgentEvent objects as JSON for a given generation.

    The client connects before (or after) triggering POST /api/generate.
    Events are pushed as they occur; the socket closes when the generation
    completes or errors, or when the client disconnects.
    """
    await websocket.accept()

    # Send a connected confirmation
    await websocket.send_json({
        "type": "connected",
        "generation_id": generation_id,
        "message": "Subscribed to generation events",
    })

    queue = event_bus.subscribe(generation_id)

    try:
        while True:
            try:
                # Wait for events with a timeout so we can detect disconnects
                event = await asyncio.wait_for(queue.get(), timeout=120.0)
            except asyncio.TimeoutError:
                # Send a keepalive ping
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break
                continue

            # Serialize the AgentEvent to JSON (nested under payload for frontend)
            agent_event_payload = {
                "generation_id": event.generation_id,
                "agent_id": event.agent_id.value,
                "status": event.status.value,
                "message": event.message,
                "detail": event.detail,
                "timestamp": event.timestamp.isoformat(),
            }

            await websocket.send_json({
                "type": "agent_event",
                "payload": agent_event_payload,
            })

            # If this was a terminal event for the orchestrator, close
            if (
                event.agent_id.value == "orchestrator"
                and event.status.value in ("completed", "error")
            ):
                terminal_type = (
                    "generation_completed"
                    if event.status.value == "completed"
                    else "generation_error"
                )
                await websocket.send_json({
                    "type": terminal_type,
                    "payload": {
                        "generation_id": generation_id,
                        "status": event.status.value,
                        "compliance_report": event.detail.get("compliance_report") if event.detail else None,
                        "message": event.message,
                    },
                })
                # Close cleanly so client doesn't retry
                await websocket.close(code=1000, reason="Generation complete")
                event_bus.unsubscribe(generation_id, queue)
                return

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for generation %s", generation_id)
    except Exception:
        logger.exception("WebSocket error for generation %s", generation_id)
    finally:
        event_bus.unsubscribe(generation_id, queue)

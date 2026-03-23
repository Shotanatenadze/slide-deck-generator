"""
In-memory event bus for streaming agent events to WebSocket clients.

Each generation_id has a list of asyncio.Queue subscribers.
Agents publish AgentEvent objects; WebSocket handlers subscribe and relay.

Events are stored in a history buffer so that late-connecting subscribers
(e.g. WebSocket connects after generation has already started) receive
all past events on subscribe.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.schemas import AgentEvent

_subscribers: dict[str, list[asyncio.Queue]] = {}
_history: dict[str, list[AgentEvent]] = {}


async def publish(generation_id: str, event: AgentEvent) -> None:
    """Push an event to every subscriber queue and store in history."""
    _history.setdefault(generation_id, []).append(event)

    queues = _subscribers.get(generation_id, [])
    for q in queues:
        await q.put(event)


def subscribe(generation_id: str) -> asyncio.Queue:
    """Create and register a new subscriber queue for this generation.

    Replays all past events so late connectors don't miss anything.
    """
    q: asyncio.Queue = asyncio.Queue()

    # Replay event history
    for event in _history.get(generation_id, []):
        q.put_nowait(event)

    _subscribers.setdefault(generation_id, []).append(q)
    return q


def unsubscribe(generation_id: str, queue: asyncio.Queue) -> None:
    """Remove a subscriber queue.  Safe to call even if already removed."""
    queues = _subscribers.get(generation_id, [])
    try:
        queues.remove(queue)
    except ValueError:
        pass
    # Clean up empty lists
    if not queues and generation_id in _subscribers:
        del _subscribers[generation_id]

"""
Abstract base class for all agents.

Provides:
- Event emission via the event bus
- A generic Claude tool-use loop (`call_claude`)
- Abstract hooks for subclasses: run, execute_tool, get_tools
"""

from __future__ import annotations

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

import anthropic

from app.agents import event_bus
from app.models.enums import AgentId, AgentStatus
from app.models.schemas import AgentEvent

logger = logging.getLogger(__name__)

# Pacing delay between events so the frontend can visualize each step
EVENT_PACE_SECONDS = 0.35

MODEL = "claude-opus-4-6"
MAX_TOOL_ROUNDS = 20  # safety limit


class BaseAgent(ABC):
    """Base class every agent inherits from."""

    def __init__(
        self,
        agent_id: AgentId,
        generation_id: str,
        anthropic_client: anthropic.Anthropic | None = None,
    ) -> None:
        self.agent_id = agent_id
        self.generation_id = generation_id
        self.client = anthropic_client

    # ------------------------------------------------------------------
    # Event helpers
    # ------------------------------------------------------------------

    async def emit(
        self,
        status: AgentStatus,
        message: str,
        detail: dict | None = None,
    ) -> None:
        event = AgentEvent(
            generation_id=self.generation_id,
            agent_id=self.agent_id,
            status=status,
            message=message,
            detail=detail,
            timestamp=datetime.utcnow(),
        )
        await event_bus.publish(self.generation_id, event)
        # Pace events so the frontend can render each step visually
        await asyncio.sleep(EVENT_PACE_SECONDS)

    # ------------------------------------------------------------------
    # Claude tool-use loop
    # ------------------------------------------------------------------

    async def call_claude(
        self,
        system_prompt: str,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> str:
        """
        Run the Anthropic messages loop with automatic tool execution.

        Returns the final text response from Claude.
        """
        if self.client is None:
            raise RuntimeError("Anthropic client not configured")

        await self.emit(AgentStatus.THINKING, "Reasoning...")

        kwargs: dict[str, Any] = {
            "model": MODEL,
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": list(messages),  # mutable copy
        }
        if tools:
            kwargs["tools"] = tools

        for _round in range(MAX_TOOL_ROUNDS):
            response = self.client.messages.create(**kwargs)

            # Separate text and tool_use blocks
            text_parts: list[str] = []
            tool_uses: list[dict] = []
            for block in response.content:
                if block.type == "text":
                    text_parts.append(block.text)
                elif block.type == "tool_use":
                    tool_uses.append(
                        {"id": block.id, "name": block.name, "input": block.input}
                    )

            # If no tool calls, we're done
            if not tool_uses:
                final_text = "\n".join(text_parts)
                await self.emit(
                    AgentStatus.TOOL_RESULT,
                    "Agent finished reasoning",
                    {"text": final_text[:500]},
                )
                return final_text

            # Process each tool call
            tool_results: list[dict] = []
            for tu in tool_uses:
                await self.emit(
                    AgentStatus.TOOL_CALL,
                    f"Calling tool: {tu['name']}",
                    {"tool": tu["name"], "input_keys": list(tu["input"].keys())},
                )

                try:
                    result_str = await self.execute_tool(tu["name"], tu["input"])
                except Exception as exc:
                    logger.exception("Tool %s failed", tu["name"])
                    result_str = json.dumps({"error": str(exc)})

                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tu["id"],
                        "content": result_str,
                    }
                )

                await self.emit(
                    AgentStatus.TOOL_RESULT,
                    f"Tool {tu['name']} returned result",
                )

            # Append assistant turn + tool results, then loop
            kwargs["messages"].append({"role": "assistant", "content": response.content})
            kwargs["messages"].append({"role": "user", "content": tool_results})

        # Safety: exceeded max rounds
        return "Max tool-use rounds exceeded."

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    async def run(self, **kwargs: Any) -> dict:
        """Execute the agent's primary task.  Subclasses must implement."""
        ...

    @abstractmethod
    async def execute_tool(self, name: str, tool_input: dict) -> str:
        """Dispatch a tool call.  Return a JSON string result."""
        ...

    @abstractmethod
    def get_tools(self) -> list[dict]:
        """Return Anthropic-format tool definitions."""
        ...

"""
Market Data Agent — processes free-text market context into structured sections.

Lightweight agent: takes market_context text (provided by analyst) and
extracts structured sections for inclusion in the deck.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.agents.base import BaseAgent
from app.models.enums import AgentId, AgentStatus

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are the Market Data Agent. Your job is to take free-text market commentary
and structure it into labeled sections suitable for a quarterly client presentation.

Typical sections include:
- Economic Overview
- Fixed Income Markets
- Equity Markets
- Credit Markets
- Outlook

Use the parse_market_text tool to extract and structure the text.
Return a summary of the sections you identified.
"""


class MarketDataAgent(BaseAgent):
    def __init__(self, generation_id: str, anthropic_client=None):
        super().__init__(AgentId.MARKET_DATA, generation_id, anthropic_client)

    def get_tools(self) -> list[dict]:
        return [
            {
                "name": "parse_market_text",
                "description": "Extract structured sections from free-text market commentary.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "Raw market commentary text",
                        }
                    },
                    "required": ["text"],
                },
            },
        ]

    async def execute_tool(self, name: str, tool_input: dict) -> str:
        if name == "parse_market_text":
            text = tool_input.get("text", "")
            sections = _extract_sections(text)
            return json.dumps({
                "status": "success",
                "section_count": len(sections),
                "sections": sections,
            })
        return json.dumps({"error": f"Unknown tool: {name}"})

    async def run(self, **kwargs) -> dict:
        """
        Process market context text.

        kwargs:
          - market_context: str | None — free-text market commentary
        """
        market_context = kwargs.get("market_context") or ""

        await self.emit(AgentStatus.STARTED, "Market Data Agent started")

        if not market_context.strip():
            await self.emit(
                AgentStatus.COMPLETED,
                "No market context provided — skipping market update slides",
            )
            return {"sections": [], "raw_text": ""}

        # If we have a Claude client, let it decide how to parse
        if self.client:
            messages = [
                {
                    "role": "user",
                    "content": (
                        "Parse the following market commentary into structured sections:\n\n"
                        f"{market_context}"
                    ),
                }
            ]
            try:
                result_text = await self.call_claude(
                    SYSTEM_PROMPT, messages, self.get_tools()
                )
                # Claude may have called parse_market_text via tool loop.
                # We also do a direct parse to ensure we have data.
                sections = _extract_sections(market_context)
                await self.emit(
                    AgentStatus.COMPLETED,
                    f"Market data processed: {len(sections)} sections",
                )
                return {"sections": sections, "raw_text": market_context}
            except Exception as e:
                logger.warning("Claude call failed, falling back to direct parse: %s", e)

        # Direct / fallback
        await self.emit(AgentStatus.THINKING, "Analyzing market commentary structure...")
        await self.emit(AgentStatus.TOOL_CALL, "Calling parse_market_text to extract sections")
        sections = _extract_sections(market_context)
        section_names = [s.get("title", "") for s in sections]
        await self.emit(AgentStatus.TOOL_RESULT, f"Extracted {len(sections)} sections: {', '.join(section_names)}")
        await self.emit(
            AgentStatus.COMPLETED,
            f"Market data structured into {len(sections)} narrative sections",
        )
        return {"sections": sections, "raw_text": market_context}


def _extract_sections(text: str) -> list[dict]:
    """
    Split free-text market commentary into titled sections.

    Heuristic: look for lines that look like headers (short, possibly
    all-caps, followed by longer body text). Falls back to a single
    section if no structure is detected.
    """
    if not text or not text.strip():
        return []

    lines = text.strip().split("\n")

    # Try to detect markdown-style headers or ALL-CAPS headers
    sections: list[dict] = []
    current_title = ""
    current_body: list[str] = []

    header_re = re.compile(r"^(?:#{1,3}\s+)?([A-Z][A-Za-z\s&/,\-:]{2,60})$")

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current_body:
                current_body.append("")
            continue

        # Check if this looks like a header
        match = header_re.match(stripped)
        is_short = len(stripped) < 60
        is_caps = stripped == stripped.upper() and len(stripped) > 3
        is_header = (match is not None and is_short) or (is_caps and is_short)

        if is_header and current_body:
            # Save previous section
            sections.append({
                "title": current_title,
                "content": "\n".join(current_body).strip(),
            })
            current_title = stripped.strip("#").strip()
            current_body = []
        elif is_header and not current_body:
            current_title = stripped.strip("#").strip()
        else:
            current_body.append(stripped)

    # Save last section
    if current_title or current_body:
        sections.append({
            "title": current_title or "Market Commentary",
            "content": "\n".join(current_body).strip(),
        })

    # If we ended up with no sections, wrap the whole text as one
    if not sections:
        sections = [{"title": "Market Commentary", "content": text.strip()}]

    return sections

"""
Orchestrator Agent — coordinates all specialist agents.

Deterministic dispatch (no Claude call needed for orchestration itself):
1. Parse uploaded files via PortfolioAgent + MarketDataAgent in parallel
2. Build deck via DeckBuilderAgent
3. Run ComplianceAgent on portfolio data
4. Return combined result
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import anthropic

# Extra delay between orchestrator stages for visual pacing
STAGE_DELAY = 0.5

from app.agents.base import BaseAgent
from app.agents.portfolio import PortfolioAgent
from app.agents.market_data import MarketDataAgent
from app.agents.compliance import ComplianceAgent
from app.agents.deck_builder import DeckBuilderAgent
from app.config import settings
from app.models.enums import AgentId, AgentStatus, GenerationStatus
from app.storage.local import list_uploads

logger = logging.getLogger(__name__)

# In-memory generation state store
_generations: dict[str, dict] = {}


def get_generation(generation_id: str) -> dict | None:
    return _generations.get(generation_id)


class OrchestratorAgent(BaseAgent):
    def __init__(self, generation_id: str, anthropic_client=None):
        super().__init__(AgentId.ORCHESTRATOR, generation_id, anthropic_client)

    def get_tools(self) -> list[dict]:
        # Orchestrator does not use Claude tools — purely deterministic dispatch
        return []

    async def execute_tool(self, name: str, tool_input: dict) -> str:
        return '{"error": "Orchestrator has no tools"}'

    async def run(self, **kwargs) -> dict:
        """
        Orchestrate the full deck generation pipeline.

        kwargs:
          - generation_id: str
          - client_name: str
          - analyst_prompt: str
          - market_context: str | None
        """
        generation_id = kwargs.get("generation_id", self.generation_id)
        client_name = kwargs.get("client_name", "Client")
        analyst_prompt = kwargs.get("analyst_prompt", "")
        market_context = kwargs.get("market_context")

        # Initialize generation state
        _generations[generation_id] = {
            "status": GenerationStatus.GENERATING,
            "client_name": client_name,
        }

        await self.emit(AgentStatus.STARTED, "Orchestrator started")

        # Build Anthropic client (if API key is configured)
        claude_client = None
        if settings.ANTHROPIC_API_KEY:
            try:
                claude_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            except Exception as e:
                logger.warning("Could not initialize Anthropic client: %s", e)

        # ----------------------------------------------------------------
        # Step 1: Dispatch Portfolio + MarketData agents in parallel
        # ----------------------------------------------------------------
        await self.emit(
            AgentStatus.THINKING,
            "Analyzing request and planning agent dispatch...",
        )

        file_paths = list_uploads(generation_id)
        if not file_paths:
            error_msg = "No uploaded files found for this generation"
            await self.emit(AgentStatus.ERROR, error_msg)
            _generations[generation_id]["status"] = GenerationStatus.ERROR
            _generations[generation_id]["error"] = error_msg
            return {"error": error_msg}

        await asyncio.sleep(STAGE_DELAY)
        await self.emit(
            AgentStatus.TOOL_CALL,
            "Dispatching Portfolio and Market Data agents in parallel",
        )

        await asyncio.sleep(STAGE_DELAY)
        portfolio_agent = PortfolioAgent(generation_id, claude_client)
        market_agent = MarketDataAgent(generation_id, claude_client)

        portfolio_task = asyncio.create_task(
            portfolio_agent.run(
                file_paths=file_paths,
                client_name=client_name,
            )
        )
        market_task = asyncio.create_task(
            market_agent.run(market_context=market_context)
        )

        try:
            portfolio_data, market_data = await asyncio.gather(
                portfolio_task, market_task
            )
        except Exception as e:
            error_msg = f"Agent dispatch failed: {e}"
            logger.exception(error_msg)
            await self.emit(AgentStatus.ERROR, error_msg)
            _generations[generation_id]["status"] = GenerationStatus.ERROR
            _generations[generation_id]["error"] = error_msg
            return {"error": error_msg}

        if "error" in portfolio_data and not portfolio_data.get("performance"):
            error_msg = f"Portfolio parsing failed: {portfolio_data['error']}"
            await self.emit(AgentStatus.ERROR, error_msg)
            _generations[generation_id]["status"] = GenerationStatus.ERROR
            _generations[generation_id]["error"] = error_msg
            return {"error": error_msg}

        await self.emit(
            AgentStatus.TOOL_RESULT,
            "Portfolio and Market Data agents completed",
        )

        await asyncio.sleep(STAGE_DELAY)

        # ----------------------------------------------------------------
        # Step 2: Dispatch DeckBuilder + Compliance in parallel
        # ----------------------------------------------------------------
        await self.emit(
            AgentStatus.TOOL_CALL,
            "Dispatching Deck Builder and Compliance agents",
        )

        await asyncio.sleep(STAGE_DELAY)

        deck_agent = DeckBuilderAgent(generation_id, claude_client)
        compliance_agent = ComplianceAgent(generation_id, claude_client)

        deck_task = asyncio.create_task(
            deck_agent.run(
                portfolio_data=portfolio_data,
                market_data=market_data,
                analyst_prompt=analyst_prompt,
                generation_id=generation_id,
            )
        )
        compliance_task = asyncio.create_task(
            compliance_agent.run(portfolio_data=portfolio_data)
        )

        try:
            deck_result, compliance_result = await asyncio.gather(
                deck_task, compliance_task
            )
        except Exception as e:
            error_msg = f"Deck/Compliance agents failed: {e}"
            logger.exception(error_msg)
            await self.emit(AgentStatus.ERROR, error_msg)
            _generations[generation_id]["status"] = GenerationStatus.ERROR
            _generations[generation_id]["error"] = error_msg
            return {"error": error_msg}

        await self.emit(
            AgentStatus.TOOL_RESULT,
            "Deck Builder and Compliance agents completed",
        )

        # ----------------------------------------------------------------
        # Step 3: Assemble final result
        # ----------------------------------------------------------------
        deck_path = deck_result.get("deck_path")
        if not deck_path:
            error_msg = deck_result.get("error", "Unknown deck build error")
            await self.emit(AgentStatus.ERROR, error_msg)
            _generations[generation_id]["status"] = GenerationStatus.ERROR
            _generations[generation_id]["error"] = error_msg
            return {"error": error_msg}

        result = {
            "generation_id": generation_id,
            "status": GenerationStatus.COMPLETED,
            "deck_path": deck_path,
            "compliance_report": compliance_result,
        }

        _generations[generation_id].update({
            "status": GenerationStatus.COMPLETED,
            "deck_path": deck_path,
            "compliance_report": compliance_result,
        })

        await self.emit(
            AgentStatus.COMPLETED,
            f"Generation complete! Deck: {deck_path}",
            {
                "deck_path": deck_path,
                "compliance_status": compliance_result.get("overall_status", "UNKNOWN"),
                "compliance_report": compliance_result,
            },
        )

        return result

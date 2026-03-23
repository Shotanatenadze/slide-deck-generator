"""
Deck Builder Agent — orchestrates PPTX assembly.

Uses Claude to generate per-slide commentary based on the analyst prompt
and portfolio data, then delegates to the deterministic pptx_builder tool.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from app.agents.base import MODEL, BaseAgent
from app.models.enums import AgentId, AgentStatus
from app.tools import pptx_builder

logger = logging.getLogger(__name__)

COMMENTARY_SYSTEM_PROMPT = """\
You are a senior investment analyst at Performa, a boutique asset management firm \
serving captive insurance clients. You write clear, professional slide commentary \
for quarterly client review decks.

Given portfolio data and an analyst prompt, generate commentary for each slide \
in the deck. The commentary should be tailored to the analyst's instructions — \
for example, if they ask for a "board meeting" deck, use executive language and \
highlight strategic themes; if they ask for a "deep dive", include more granular \
analysis.

Return valid JSON with these keys:
{
  "deck_title": "subtitle for the title slide (e.g. 'Q1 2025 Board Review')",
  "allocation_commentary": "1-2 sentences on asset allocation (highlight notable positions, changes)",
  "performance_commentary": "1-2 sentences on performance (relative to benchmark, trends)",
  "rollforward_commentary": "1 sentence on cash flows (contributions, withdrawals, income)",
  "sma_commentary": "1-2 sentences on SMA portfolio (duration, credit quality, sector themes)",
  "market_commentary": "2-3 sentences expanding on the market context provided",
  "key_takeaways": ["bullet 1", "bullet 2", "bullet 3"]
}

Keep commentary concise and data-driven. Reference specific numbers from the data. \
Do NOT fabricate numbers — use only what is provided.
"""


class DeckBuilderAgent(BaseAgent):
    def __init__(self, generation_id: str, anthropic_client=None):
        super().__init__(AgentId.DECK_BUILDER, generation_id, anthropic_client)
        self._deck_path: str | None = None

    def get_tools(self) -> list[dict]:
        return [
            {
                "name": "generate_commentary",
                "description": "Use Claude to generate per-slide commentary tailored to the analyst prompt.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "data_summary": {
                            "type": "string",
                            "description": "Summary of portfolio data for commentary generation",
                        },
                        "analyst_prompt": {
                            "type": "string",
                            "description": "The analyst's instructions for the deck",
                        },
                    },
                    "required": ["data_summary", "analyst_prompt"],
                },
            },
            {
                "name": "build_deck",
                "description": "Build the PowerPoint deck with commentary. Returns the file path.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "build": {"type": "boolean"},
                    },
                    "required": ["build"],
                },
            },
        ]

    async def execute_tool(self, name: str, tool_input: dict) -> str:
        if name == "generate_commentary":
            return json.dumps({"status": "handled_inline"})

        elif name == "build_deck":
            if not self._build_data:
                return json.dumps({"error": "No build data set"})
            try:
                path = pptx_builder.build_deck(
                    portfolio_data=self._build_data.get("portfolio_data", {}),
                    market_data=self._build_data.get("market_data"),
                    compliance_report=self._build_data.get("compliance_report"),
                    analyst_prompt=self._build_data.get("analyst_prompt", ""),
                    generation_id=self._build_data.get("generation_id"),
                    commentary=self._build_data.get("commentary"),
                )
                self._deck_path = path
                return json.dumps({"status": "success", "path": path})
            except Exception as e:
                logger.exception("Deck build failed")
                return json.dumps({"status": "error", "error": str(e)})

        return json.dumps({"error": f"Unknown tool: {name}"})

    async def run(self, **kwargs) -> dict:
        self._build_data = kwargs

        portfolio_data = kwargs.get("portfolio_data", {})
        market_data = kwargs.get("market_data")
        analyst_prompt = kwargs.get("analyst_prompt", "")

        await self.emit(AgentStatus.STARTED, "Deck Builder Agent started")

        has_perf = bool(portfolio_data.get("performance"))
        has_alloc = bool(portfolio_data.get("allocation"))
        has_rf = bool(portfolio_data.get("roll_forward"))
        has_sma = bool(portfolio_data.get("sma_holdings") or portfolio_data.get("sma_summary"))
        has_market = bool(market_data and market_data.get("sections"))

        await self.emit(
            AgentStatus.THINKING,
            f"Planning deck: slides={sum([1, has_market, has_alloc, has_perf, has_rf, has_sma*3])}",
        )

        # Step 1: Generate commentary using Claude
        commentary = await self._generate_commentary(portfolio_data, market_data, analyst_prompt)
        self._build_data["commentary"] = commentary

        # Step 2: Build deck
        await self._build(portfolio_data, commentary)

        if self._deck_path:
            await self.emit(AgentStatus.COMPLETED, f"Deck generated: {self._deck_path}")
            return {"deck_path": self._deck_path}
        else:
            await self.emit(AgentStatus.ERROR, "Deck generation failed")
            return {"error": "Deck generation failed"}

    async def _generate_commentary(
        self,
        portfolio_data: dict,
        market_data: dict | None,
        analyst_prompt: str,
    ) -> dict:
        """Generate per-slide commentary using Claude or fallback."""
        # Build data summary for Claude
        data_summary = self._build_data_summary(portfolio_data, market_data)

        await self.emit(AgentStatus.TOOL_CALL, "Generating slide commentary from analyst prompt")

        if self.client:
            try:
                response = self.client.messages.create(
                    model=MODEL,
                    max_tokens=2048,
                    system=COMMENTARY_SYSTEM_PROMPT,
                    messages=[
                        {
                            "role": "user",
                            "content": (
                                f"Analyst prompt: {analyst_prompt}\n\n"
                                f"Portfolio data summary:\n{data_summary}\n\n"
                                f"Market context: {market_data.get('raw_text', 'Not provided') if market_data else 'Not provided'}\n\n"
                                "Generate the JSON commentary object."
                            ),
                        }
                    ],
                )
                text = response.content[0].text
                # Extract JSON from response
                commentary = self._parse_json_response(text)
                if commentary:
                    await self.emit(
                        AgentStatus.TOOL_RESULT,
                        f"Commentary generated: {commentary.get('deck_title', 'Quarterly Review')}",
                    )
                    return commentary
            except Exception as e:
                logger.warning("Claude commentary generation failed: %s", e)

        # Fallback: generate basic commentary from data
        commentary = self._fallback_commentary(portfolio_data, market_data, analyst_prompt)
        await self.emit(
            AgentStatus.TOOL_RESULT,
            f"Commentary prepared: {commentary.get('deck_title', 'Quarterly Review')}",
        )
        return commentary

    def _build_data_summary(self, portfolio_data: dict, market_data: dict | None) -> str:
        """Build a concise data summary string for Claude."""
        parts = []
        parts.append(f"Client: {portfolio_data.get('client_name', 'Client')}")
        parts.append(f"Type: {portfolio_data.get('client_type', 'AGG')}")

        # Performance
        perf = portfolio_data.get("performance", [])
        if perf:
            parts.append(f"Performance periods: {len(perf)}")
            for p in perf[:3]:
                ret = p.get("total_return")
                idx = p.get("index_return")
                ret_str = f"{ret*100:.2f}%" if ret is not None else "N/A"
                idx_str = f"{idx*100:.2f}%" if idx is not None else "N/A"
                parts.append(f"  {p.get('period', '?')}: Net={ret_str}, Index={idx_str}")

        # Allocation
        alloc = portfolio_data.get("allocation", [])
        if alloc:
            total_mv = sum((a.get("market_value") or 0) for a in alloc)
            parts.append(f"Total Market Value: ${total_mv:,.0f}")
            parts.append(f"Allocations: {len(alloc)} positions")
            for a in alloc[:5]:
                pct = a.get("actual_pct")
                pct_str = f"{pct*100:.1f}%" if pct else "N/A"
                mv = a.get("market_value") or 0
                parts.append(f"  {a.get('strategy', '?')}: ${mv:,.0f} ({pct_str})")

        # Roll forward
        rf = portfolio_data.get("roll_forward", [])
        if rf:
            parts.append(f"Roll Forward: {len(rf)} line items")
            for r in rf[:3]:
                val = r.get("value") or 0
                parts.append(f"  {r.get('label', '?')}: ${val:,.0f}")

        # SMA
        sma = portfolio_data.get("sma_summary") or {}
        if sma:
            parts.append(f"SMA Total MV: ${(sma.get('total_market_value') or 0):,.0f}")
            parts.append(f"SMA Holdings: {sma.get('num_holdings', 0)}")
            parts.append(f"SMA Avg Duration: {(sma.get('avg_duration') or 0):.2f}")
            parts.append(f"SMA Avg Yield: {(sma.get('avg_yield') or 0):.2f}%")

        return "\n".join(parts)

    def _parse_json_response(self, text: str) -> dict | None:
        """Extract JSON from Claude's response (handles markdown code blocks)."""
        import re
        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # Try extracting from code block
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        # Try finding first { to last }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(text[start:end+1])
            except json.JSONDecodeError:
                pass
        return None

    def _fallback_commentary(
        self, portfolio_data: dict, market_data: dict | None, analyst_prompt: str
    ) -> dict:
        """Generate basic commentary without Claude based on data and prompt."""
        client_name = portfolio_data.get("client_name", "Client")
        perf = portfolio_data.get("performance", [])
        alloc = portfolio_data.get("allocation", [])
        sma = portfolio_data.get("sma_summary", {})

        # Derive deck title from prompt
        prompt_lower = analyst_prompt.lower()
        if "board" in prompt_lower:
            deck_title = "Board of Directors — Quarterly Investment Review"
        elif "deep dive" in prompt_lower:
            deck_title = "Portfolio Deep Dive Analysis"
        elif "check-in" in prompt_lower or "quick" in prompt_lower:
            deck_title = "Quarterly Check-in Summary"
        elif "sma" in prompt_lower:
            deck_title = "Fixed Income SMA — Detailed Analysis"
        else:
            deck_title = "Quarterly Investment Review"

        # Performance commentary
        perf_comment = ""
        if perf:
            qtd = next((p for p in perf if "quarter" in (p.get("period") or "").lower()), None)
            ytd = next((p for p in perf if "year to date" in (p.get("period") or "").lower()), None)
            if qtd and qtd.get("total_return") is not None:
                ret = qtd["total_return"] * 100
                idx = (qtd.get("index_return") or 0) * 100
                diff = ret - idx
                direction = "outperformed" if diff > 0 else "trailed"
                perf_comment = f"The portfolio returned {ret:.2f}% for the quarter, {direction} the benchmark by {abs(diff):.2f}%."
            if ytd and ytd.get("total_return") is not None:
                perf_comment += f" Year-to-date return stands at {ytd['total_return']*100:.2f}%."

        # Allocation commentary
        alloc_comment = ""
        if alloc:
            total_mv = sum(a.get("market_value", 0) or 0 for a in alloc)
            top = sorted(alloc, key=lambda a: a.get("market_value", 0) or 0, reverse=True)[:2]
            top_names = [a.get("strategy", "?") for a in top]
            alloc_comment = (
                f"Total portfolio value is ${total_mv:,.0f}. "
                f"Largest allocations: {', '.join(top_names)}."
            )

        # SMA commentary
        sma_comment = ""
        if sma:
            sma_comment = (
                f"The SMA portfolio holds {sma.get('num_holdings', 0)} positions "
                f"with an average duration of {sma.get('avg_duration', 0):.2f} years "
                f"and average yield of {sma.get('avg_yield', 0):.2f}%."
            )

        # Key takeaways
        takeaways = []
        if perf_comment:
            takeaways.append(perf_comment.split(".")[0] + ".")
        if alloc_comment:
            takeaways.append(alloc_comment.split(".")[0] + ".")
        if sma_comment:
            takeaways.append(sma_comment.split(".")[0] + ".")

        return {
            "deck_title": deck_title,
            "allocation_commentary": alloc_comment,
            "performance_commentary": perf_comment,
            "rollforward_commentary": "Portfolio activity reflects contributions, withdrawals, and investment income for the period.",
            "sma_commentary": sma_comment,
            "market_commentary": "",
            "key_takeaways": takeaways or ["Portfolio remains within IPS guidelines."],
        }

    async def _build(self, portfolio_data: dict, commentary: dict) -> None:
        """Build the PPTX file."""

        # Plan slides
        await self.emit(AgentStatus.TOOL_CALL, "Assembling slide layout plan")
        slides = ["Title", "Section Divider"]
        if self._build_data.get("market_data", {}).get("sections"):
            slides.append("Market Update")
        slides.extend(["Asset Allocation", "Performance", "Roll Forward"])
        if portfolio_data.get("sma_holdings") or portfolio_data.get("sma_summary"):
            slides.extend(["SMA Statistics", "SMA Performance", "SMA Holdings"])
        slides.append("Disclaimer")
        await self.emit(AgentStatus.TOOL_RESULT, f"Slide plan: {len(slides)} slides — {', '.join(slides)}")

        # Build
        await self.emit(AgentStatus.TOOL_CALL, "Rendering PowerPoint deck with commentary")
        try:
            path = pptx_builder.build_deck(
                portfolio_data=portfolio_data,
                market_data=self._build_data.get("market_data"),
                compliance_report=self._build_data.get("compliance_report"),
                analyst_prompt=self._build_data.get("analyst_prompt", ""),
                generation_id=self._build_data.get("generation_id"),
                commentary=commentary,
            )
            self._deck_path = path
            await self.emit(AgentStatus.TOOL_RESULT, f"PowerPoint deck assembled: {len(slides)} slides generated")
        except Exception as e:
            logger.exception("Deck build failed")
            await self.emit(AgentStatus.ERROR, f"Build failed: {e}")

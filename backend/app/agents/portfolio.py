"""
Portfolio Agent — parses uploaded Excel and PDF files into structured data.

All files are sent to Claude Opus 4.6 for extraction.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.agents.base import BaseAgent
from app.models.enums import AgentId, AgentStatus
from app.tools import excel_parser

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are the Portfolio Agent in a multi-agent slide deck generation system.
Your job is to parse uploaded files (Excel or PDF) and extract ALL available
financial data into structured JSON.

You have these tools:
- parse_file: Parses any uploaded file (Excel .xlsx or PDF .pdf) using AI to
  extract portfolio data matching the PortfolioData schema. Works with Clearwater
  Analytics exports, SMA Holdings reports, and arbitrary financial documents.
- validate_data: Checks that the parsed data has the required fields.

Extract everything — performance, allocation, roll forward, contributions,
market value history, individual holdings, summary statistics. The system will
automatically generate slides for all available data.

Parse each uploaded file, then validate.
"""

SUPPORTED_EXTENSIONS = {".xlsx", ".xls", ".pdf"}


class PortfolioAgent(BaseAgent):
    def __init__(self, generation_id: str, anthropic_client=None):
        super().__init__(AgentId.PORTFOLIO, generation_id, anthropic_client)
        self._parsed_data: dict[str, Any] = {}

    def get_tools(self) -> list[dict]:
        return [
            {
                "name": "parse_file",
                "description": "Parse an uploaded file (Excel .xlsx or PDF .pdf) to extract portfolio data. Uses AI to interpret the file contents and return structured JSON.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Absolute path to the uploaded file (.xlsx or .pdf)",
                        }
                    },
                    "required": ["file_path"],
                },
            },
            {
                "name": "validate_data",
                "description": "Validate that parsed portfolio data has the required fields.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "has_performance": {"type": "boolean"},
                        "has_allocation": {"type": "boolean"},
                        "has_roll_forward": {"type": "boolean"},
                        "has_holdings": {"type": "boolean"},
                    },
                    "required": [],
                },
            },
        ]

    async def execute_tool(self, name: str, tool_input: dict) -> str:
        if name == "parse_file":
            try:
                client_name = self._parsed_data.get("client_name", "Client")
                result = excel_parser.parse_file_with_claude(
                    tool_input["file_path"], self.client, client_name
                )
                # Merge results
                if result.get("sma_holdings"):
                    self._parsed_data["sma_holdings"] = result["sma_holdings"]
                if result.get("sma_summary"):
                    self._parsed_data["sma_summary"] = result["sma_summary"]
                for key in ("performance", "allocation", "roll_forward", "contributions", "mv_history"):
                    if result.get(key):
                        self._parsed_data[key] = result[key]
                return json.dumps({
                    "status": "success",
                    "performance_rows": len(result.get("performance", [])),
                    "allocation_rows": len(result.get("allocation", [])),
                    "roll_forward_rows": len(result.get("roll_forward", [])),
                    "holdings_count": len(result.get("sma_holdings", [])),
                })
            except Exception as e:
                logger.exception("File parse failed")
                return json.dumps({"status": "error", "error": str(e)})

        elif name == "validate_data":
            issues: list[str] = []
            if not self._parsed_data.get("performance"):
                issues.append("Missing performance data")
            if not self._parsed_data.get("allocation"):
                issues.append("Missing allocation data")
            return json.dumps({
                "valid": len(issues) == 0,
                "issues": issues,
            })

        return json.dumps({"error": f"Unknown tool: {name}"})

    async def run(self, **kwargs) -> dict:
        """
        Parse uploaded Excel or PDF files.

        kwargs:
          - file_paths: list[str] — absolute paths to uploaded files
          - client_name: str
        """
        file_paths: list[str] = kwargs.get("file_paths", [])
        client_name: str = kwargs.get("client_name", "Client")

        await self.emit(AgentStatus.STARTED, "Portfolio Agent started")

        if not file_paths:
            await self.emit(AgentStatus.ERROR, "No files provided")
            return {"error": "No files provided"}

        await self._direct_parse(file_paths, client_name)

        # Validate data
        await self.emit(AgentStatus.TOOL_CALL, "Calling validate_data to check completeness")
        issues = []
        if not self._parsed_data.get("performance"):
            issues.append("Missing performance data")
        if not self._parsed_data.get("allocation"):
            issues.append("Missing allocation data")
        if issues:
            await self.emit(AgentStatus.TOOL_RESULT, f"Validation warnings: {', '.join(issues)}")
        else:
            await self.emit(AgentStatus.TOOL_RESULT, "All data validated successfully")

        # Assemble result
        self._parsed_data["client_name"] = client_name

        await self.emit(AgentStatus.COMPLETED, "Portfolio data parsed and validated")
        return self._parsed_data

    async def _direct_parse(
        self, file_paths: list[str], client_name: str = "Client"
    ) -> None:
        """Parse all uploaded files via Claude (sequentially to respect rate limits)."""
        await self.emit(AgentStatus.THINKING, "Analyzing uploaded files...")
        self._parsed_data["client_name"] = client_name

        # Filter to supported files
        supported = [
            fp for fp in file_paths if Path(fp).suffix.lower() in SUPPORTED_EXTENSIONS
        ]
        if not supported:
            await self.emit(AgentStatus.ERROR, "No supported files found")
            return

        for fp in supported:
            fname = fp.split("/")[-1]
            await self.emit(AgentStatus.TOOL_CALL, f"Parsing {fname} with Claude...")

            try:
                result = excel_parser.parse_file_with_claude(fp, self.client, client_name)
            except Exception as exc:
                logger.exception("Parse failed for %s: %s", fp, exc)
                await self.emit(AgentStatus.ERROR, f"Failed to parse {fname}")
                continue

            # Merge results
            if result.get("sma_holdings"):
                self._parsed_data["sma_holdings"] = result["sma_holdings"]
            if result.get("sma_summary"):
                self._parsed_data["sma_summary"] = result["sma_summary"]
            for key in ("performance", "allocation", "roll_forward", "contributions", "mv_history"):
                if result.get(key):
                    self._parsed_data[key] = result[key]

            perf_count = len(result.get("performance", []))
            alloc_count = len(result.get("allocation", []))
            holdings_count = len(result.get("sma_holdings", []))
            await self.emit(
                AgentStatus.TOOL_RESULT,
                f"Parsed {fname}: {perf_count} performance, {alloc_count} allocations, {holdings_count} holdings",
            )

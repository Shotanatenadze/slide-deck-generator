"""
Compliance Agent — validates portfolio data against IPS rules and regulations.

Uses example Vermont RRG captive insurance rules as the default ruleset.
In production, rules would be loaded per-client from a database.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.agents.base import BaseAgent
from app.models.enums import AgentId, AgentStatus

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are the Compliance Agent for a captive insurance asset management firm.
Your job is to review portfolio data against Investment Policy Statement (IPS)
constraints and regulatory rules.

Example rules for Vermont RRG captive insurance clients:
- Cash allocation should not exceed 10% of total portfolio
- No single equity position should exceed 5% of portfolio
- Fixed income duration should stay within +/- 20% of benchmark
- Overall equity allocation should not exceed client's IPS maximum
- Credit quality: at least 80% of fixed income should be investment grade (BBB-/Baa3 or higher)

Use the available tools to check allocation limits and data consistency.
Report findings as PASS, WARN, or FAIL for each check.
"""

# Default IPS rules (Vermont RRG example)
DEFAULT_RULES = {
    "max_cash_pct": 0.10,
    "max_single_equity_pct": 0.05,
    "duration_tolerance": 0.20,
    "min_investment_grade_pct": 0.80,
    "max_equity_pct": 0.60,
}

INVESTMENT_GRADE_RATINGS = {
    "AAA", "AA+", "AA", "AA-", "A+", "A", "A-",
    "BBB+", "BBB", "BBB-",
    "Aaa", "Aa1", "Aa2", "Aa3", "A1", "A2", "A3",
    "Baa1", "Baa2", "Baa3",
}


class ComplianceAgent(BaseAgent):
    def __init__(self, generation_id: str, anthropic_client=None):
        super().__init__(AgentId.COMPLIANCE, generation_id, anthropic_client)

    def get_tools(self) -> list[dict]:
        return [
            {
                "name": "check_allocation_limits",
                "description": "Check portfolio allocations against IPS rules. Returns pass/warn/fail per rule.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "allocation": {
                            "type": "array",
                            "description": "List of allocation dicts with strategy, market_value, actual_pct",
                            "items": {"type": "object"},
                        },
                        "rules": {
                            "type": "object",
                            "description": "IPS rules dict",
                        },
                    },
                    "required": ["allocation"],
                },
            },
            {
                "name": "check_data_consistency",
                "description": "Validate data completeness and internal consistency.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "portfolio_data": {
                            "type": "object",
                            "description": "Full portfolio data dict",
                        },
                    },
                    "required": ["portfolio_data"],
                },
            },
        ]

    async def execute_tool(self, name: str, tool_input: dict) -> str:
        if name == "check_allocation_limits":
            allocation = tool_input.get("allocation", [])
            rules = tool_input.get("rules", DEFAULT_RULES)
            findings = _check_allocation_limits(allocation, rules)
            return json.dumps({"findings": findings})

        elif name == "check_data_consistency":
            portfolio_data = tool_input.get("portfolio_data", {})
            findings = _check_data_consistency(portfolio_data)
            return json.dumps({"findings": findings})

        return json.dumps({"error": f"Unknown tool: {name}"})

    async def run(self, **kwargs) -> dict:
        """
        Run compliance checks on portfolio data.

        kwargs:
          - portfolio_data: dict — parsed portfolio data
        """
        portfolio_data = kwargs.get("portfolio_data", {})

        await self.emit(AgentStatus.STARTED, "Compliance Agent started")
        await self.emit(AgentStatus.THINKING, "Reviewing portfolio against Vermont RRG IPS rules...")

        all_findings: list[dict] = []

        # Check allocation limits
        await self.emit(AgentStatus.TOOL_CALL, "Calling check_allocation_limits against IPS constraints")
        allocation = portfolio_data.get("allocation", [])
        alloc_findings = _check_allocation_limits(allocation, DEFAULT_RULES)
        all_findings.extend(alloc_findings)
        await self.emit(
            AgentStatus.TOOL_RESULT,
            f"Allocation checks: {len(alloc_findings)} findings",
        )

        # Check data consistency
        await self.emit(AgentStatus.TOOL_CALL, "Calling check_data_consistency for completeness")
        consistency_findings = _check_data_consistency(portfolio_data)
        all_findings.extend(consistency_findings)
        await self.emit(
            AgentStatus.TOOL_RESULT,
            f"Consistency checks: {len(consistency_findings)} findings",
        )

        # Check SMA credit quality if applicable
        sma_holdings = portfolio_data.get("sma_holdings", [])
        if sma_holdings:
            await self.emit(AgentStatus.TOOL_CALL, "Checking SMA credit quality")
            credit_findings = _check_credit_quality(sma_holdings, DEFAULT_RULES)
            all_findings.extend(credit_findings)
            await self.emit(
                AgentStatus.TOOL_RESULT,
                f"Credit quality checks: {len(credit_findings)} findings",
            )

        # If Claude is available, let it review and potentially add commentary
        if self.client:
            try:
                messages = [
                    {
                        "role": "user",
                        "content": (
                            "Review the following compliance findings and provide a brief "
                            "summary opinion:\n\n"
                            + json.dumps(all_findings, indent=2)
                        ),
                    }
                ]
                summary_text = await self.call_claude(SYSTEM_PROMPT, messages)
            except Exception as e:
                logger.warning("Claude compliance review failed: %s", e)
                summary_text = ""
        else:
            summary_text = ""

        # Aggregate status
        statuses = [f["status"] for f in all_findings]
        overall = "FAIL" if "FAIL" in statuses else ("WARN" if "WARN" in statuses else "PASS")

        result = {
            "overall_status": overall,
            "findings": all_findings,
            "summary": summary_text,
            "rules_applied": DEFAULT_RULES,
        }

        await self.emit(
            AgentStatus.COMPLETED,
            f"Compliance review complete: {overall}",
            {"overall": overall, "finding_count": len(all_findings)},
        )
        return result


def _check_allocation_limits(allocation: list[dict], rules: dict) -> list[dict]:
    """Check each allocation row against IPS limits."""
    findings: list[dict] = []

    total_mv = sum(a.get("market_value", 0) for a in allocation)
    if total_mv == 0:
        findings.append({
            "check": "total_market_value",
            "status": "WARN",
            "message": "Total market value is zero — cannot validate allocations",
        })
        return findings

    for alloc in allocation:
        strategy = alloc.get("strategy", "Unknown")
        actual_pct = alloc.get("actual_pct")
        if actual_pct is None:
            continue

        # Cash check
        if "cash" in strategy.lower():
            max_cash = rules.get("max_cash_pct", 0.10)
            if actual_pct > max_cash:
                findings.append({
                    "check": "cash_allocation",
                    "status": "WARN",
                    "message": f"Cash allocation ({actual_pct*100:.1f}%) exceeds {max_cash*100:.0f}% guideline",
                    "strategy": strategy,
                })
            else:
                findings.append({
                    "check": "cash_allocation",
                    "status": "PASS",
                    "message": f"Cash allocation ({actual_pct*100:.1f}%) within limits",
                    "strategy": strategy,
                })

    # Total allocation sum check
    total_pct = sum(a.get("actual_pct", 0) or 0 for a in allocation)
    if abs(total_pct - 1.0) > 0.02:
        findings.append({
            "check": "allocation_sum",
            "status": "WARN",
            "message": f"Allocation percentages sum to {total_pct*100:.1f}%, expected ~100%",
        })
    else:
        findings.append({
            "check": "allocation_sum",
            "status": "PASS",
            "message": "Allocation percentages sum to ~100%",
        })

    return findings


def _check_data_consistency(portfolio_data: dict) -> list[dict]:
    """Check internal data consistency."""
    findings: list[dict] = []

    # Performance data present
    perf = portfolio_data.get("performance", [])
    if not perf:
        findings.append({
            "check": "performance_data",
            "status": "WARN",
            "message": "No performance data found",
        })
    else:
        findings.append({
            "check": "performance_data",
            "status": "PASS",
            "message": f"{len(perf)} performance periods available",
        })

    # Roll forward data
    rf = portfolio_data.get("roll_forward", [])
    if not rf:
        findings.append({
            "check": "roll_forward_data",
            "status": "WARN",
            "message": "No roll forward data found",
        })
    else:
        # Check that ending MV roughly matches allocation total
        ending_row = [r for r in rf if "ending" in (r.get("label") or "").lower()]
        if ending_row:
            ending_mv = ending_row[0].get("value") or 0
            alloc_total = sum((a.get("market_value") or 0) for a in portfolio_data.get("allocation", []))
            if alloc_total > 0 and ending_mv:
                diff_pct = abs(ending_mv - alloc_total) / alloc_total
                if diff_pct > 0.05:
                    findings.append({
                        "check": "mv_consistency",
                        "status": "WARN",
                        "message": (
                            f"Roll forward ending MV (${ending_mv:,.0f}) differs from "
                            f"allocation total (${alloc_total:,.0f}) by {diff_pct*100:.1f}%"
                        ),
                    })
                else:
                    findings.append({
                        "check": "mv_consistency",
                        "status": "PASS",
                        "message": "Roll forward ending MV consistent with allocation total",
                    })

        findings.append({
            "check": "roll_forward_data",
            "status": "PASS",
            "message": f"{len(rf)} roll forward rows available",
        })

    return findings


def _check_credit_quality(holdings: list[dict], rules: dict) -> list[dict]:
    """Check SMA holdings credit quality distribution."""
    findings: list[dict] = []

    if not holdings:
        return findings

    total_mv = sum(h.get("market_value", 0) or 0 for h in holdings)
    if total_mv == 0:
        return findings

    ig_mv = 0.0
    for h in holdings:
        rating = h.get("sp_rating") or ""
        if rating in INVESTMENT_GRADE_RATINGS:
            ig_mv += h.get("market_value", 0) or 0

    ig_pct = ig_mv / total_mv if total_mv > 0 else 0
    min_ig = rules.get("min_investment_grade_pct", 0.80)

    if ig_pct < min_ig:
        findings.append({
            "check": "credit_quality",
            "status": "WARN",
            "message": (
                f"Investment grade allocation ({ig_pct*100:.1f}%) below "
                f"{min_ig*100:.0f}% guideline"
            ),
        })
    else:
        findings.append({
            "check": "credit_quality",
            "status": "PASS",
            "message": f"Investment grade allocation ({ig_pct*100:.1f}%) meets guideline",
        })

    return findings

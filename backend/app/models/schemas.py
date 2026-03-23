from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app.models.enums import AgentId, AgentStatus, ClientType, GenerationStatus


# ---------------------------------------------------------------------------
# API request / response models
# ---------------------------------------------------------------------------

class FileInfo(BaseModel):
    filename: str
    size: int
    path: str


class UploadResponse(BaseModel):
    generation_id: str
    files: List[FileInfo]


class GenerationRequest(BaseModel):
    generation_id: str
    client_name: str
    client_type: Optional[ClientType] = None
    analyst_prompt: str = ""
    market_context: Optional[str] = None


class GenerationResult(BaseModel):
    generation_id: str
    status: GenerationStatus
    deck_path: Optional[str] = None
    compliance_report: Optional[dict] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Agent event model (streamed over WebSocket)
# ---------------------------------------------------------------------------

class AgentEvent(BaseModel):
    generation_id: str
    agent_id: AgentId
    status: AgentStatus
    message: str
    detail: Optional[dict] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Portfolio data models — mirrors Clearwater Excel exports
# ---------------------------------------------------------------------------

class PerformanceRow(BaseModel):
    """One row from the Net Performance table."""
    period: str  # e.g. "Quarter to Date", "Year to Date", ...
    total_return: Optional[float] = None
    index_return: Optional[float] = None


class AllocationRow(BaseModel):
    """One row from Allocation vs Guidelines."""
    strategy: str
    market_value: float
    actual_pct: Optional[float] = None
    target_pct: Optional[float] = None  # None when "---"
    unrealized_gain_loss: Optional[float] = None


class RollForwardRow(BaseModel):
    """One row from the Portfolio Rollforward section."""
    label: str
    value: Optional[float] = None


class ContributionRow(BaseModel):
    """One row from Contribution by Strategy."""
    strategy: str
    contribution: Optional[float] = None


class MarketValueHistoryRow(BaseModel):
    """Monthly market value snapshot."""
    period_begin: str  # ISO date string
    period_end: str
    market_value: float


class SMAHolding(BaseModel):
    """Single bond holding from SMA Holdings report."""
    identifier: Optional[str] = None
    issuer: str
    sector: str
    sector_category: Optional[str] = None
    coupon: Optional[float] = None  # Duration used as proxy in sample
    duration: Optional[float] = None
    yield_to_worst: Optional[float] = None
    sp_rating: Optional[str] = None
    moody_rating: Optional[str] = None
    maturity_date: Optional[str] = None  # ISO date string
    market_value: Optional[float] = None
    pct_of_portfolio: Optional[float] = None


class SMASummary(BaseModel):
    """Aggregated SMA portfolio statistics."""
    total_market_value: float
    avg_duration: float
    avg_yield: float
    num_holdings: int
    sector_allocation: Dict[str, float] = Field(default_factory=dict)
    credit_quality: Dict[str, float] = Field(default_factory=dict)
    avg_maturity_date: Optional[str] = None
    weighted_sp_rating: Optional[str] = None
    weighted_moody_rating: Optional[str] = None


class PortfolioData(BaseModel):
    """Complete parsed portfolio data for one client."""
    client_name: str
    client_type: ClientType
    as_of_date: Optional[str] = None
    performance: List[PerformanceRow] = Field(default_factory=list)
    allocation: List[AllocationRow] = Field(default_factory=list)
    roll_forward: List[RollForwardRow] = Field(default_factory=list)
    contributions: List[ContributionRow] = Field(default_factory=list)
    mv_history: List[MarketValueHistoryRow] = Field(default_factory=list)
    sma_holdings: Optional[List[SMAHolding]] = None
    sma_summary: Optional[SMASummary] = None

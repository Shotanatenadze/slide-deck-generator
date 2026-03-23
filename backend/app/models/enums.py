from enum import Enum


class AgentId(str, Enum):
    ORCHESTRATOR = "orchestrator"
    PORTFOLIO = "portfolio"
    MARKET_DATA = "market_data"
    COMPLIANCE = "compliance"
    DECK_BUILDER = "deck_builder"


class AgentStatus(str, Enum):
    IDLE = "idle"
    STARTED = "started"
    THINKING = "thinking"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    COMPLETED = "completed"
    ERROR = "error"


class GenerationStatus(str, Enum):
    PENDING = "pending"
    UPLOADING = "uploading"
    GENERATING = "generating"
    COMPLETED = "completed"
    ERROR = "error"


class ClientType(str, Enum):
    AGG = "agg"
    SMA = "sma"
    AGG_SMA = "agg_sma"

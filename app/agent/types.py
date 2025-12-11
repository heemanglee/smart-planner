"""Agent type definitions."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AgentState(str, Enum):
    """Agent execution state."""

    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING_TOOL = "executing_tool"
    RESPONDING = "responding"
    COMPLETED = "completed"
    ERROR = "error"


class ToolCallRequest(BaseModel):
    """Tool call request from Claude."""

    id: str
    name: str
    input: dict[str, Any]


class ToolResult(BaseModel):
    """Tool execution result."""

    tool_use_id: str
    content: str
    is_error: bool = False


class AgentResponse(BaseModel):
    """Agent response model."""

    content: str = ""
    tool_calls: list[ToolCallRequest] = Field(default_factory=list)
    tool_results: list[ToolResult] = Field(default_factory=list)
    state: AgentState = AgentState.IDLE
    tokens_used: int = 0


class StreamEvent(BaseModel):
    """Streaming event model."""

    event_type: str  # text_delta, tool_use, tool_result, done, error
    content: str = ""
    tool_call: ToolCallRequest | None = None
    tool_result: ToolResult | None = None
    state: AgentState = AgentState.IDLE
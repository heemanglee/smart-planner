"""API request/response schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# Session schemas
class SessionCreate(BaseModel):
    """Create session request."""

    title: str = Field(default="New Session", max_length=100)


class SessionResponse(BaseModel):
    """Session response."""

    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int
    total_tokens: int


class SessionDetailResponse(BaseModel):
    """Session detail response with messages."""

    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list["MessageResponse"]
    total_tokens: int


class SessionListResponse(BaseModel):
    """Session list response."""

    sessions: list[SessionResponse]
    total: int


# Message schemas
class ToolCallResponse(BaseModel):
    """Tool call response."""

    id: str
    name: str
    input: dict[str, Any]
    result: dict[str, Any] | None = None


class MessageResponse(BaseModel):
    """Message response."""

    role: str
    content: str
    timestamp: datetime
    tool_calls: list[ToolCallResponse] = Field(default_factory=list)


# Chat schemas
class ChatRequest(BaseModel):
    """Chat request."""

    message: str = Field(..., min_length=1, max_length=10000)


class ChatStreamEvent(BaseModel):
    """Chat stream event."""

    event: str  # text, tool_use, tool_result, done, error
    data: str = ""
    tool_name: str | None = None
    tool_input: dict[str, Any] | None = None
    tool_result: dict[str, Any] | None = None


# Tool schemas
class ToolParameterResponse(BaseModel):
    """Tool parameter response."""

    type: str
    description: str
    enum: list[str] | None = None
    required: bool = True


class ToolResponse(BaseModel):
    """Tool response."""

    name: str
    description: str
    parameters: dict[str, ToolParameterResponse]


class ToolListResponse(BaseModel):
    """Tool list response."""

    tools: list[ToolResponse]


# Error schemas
class ErrorResponse(BaseModel):
    """Error response."""

    error: str
    detail: str | None = None
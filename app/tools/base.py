"""Base tool class for all tools."""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class ToolParameter(BaseModel):
    """Tool parameter definition."""

    type: str
    description: str
    enum: list[str] | None = None
    default: Any | None = None


class BaseTool(ABC):
    """Abstract base class for all tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name used for invocation."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for the LLM."""
        ...

    @property
    @abstractmethod
    def parameters(self) -> dict[str, ToolParameter]:
        """Tool parameters schema."""
        ...

    @property
    def required_parameters(self) -> list[str]:
        """List of required parameter names."""
        return [
            name
            for name, param in self.parameters.items()
            if param.default is None
        ]

    @abstractmethod
    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        """Execute the tool with given parameters.

        Args:
            **kwargs: Tool parameters.

        Returns:
            Tool execution result.
        """
        ...

    def to_claude_tool(self) -> dict[str, Any]:
        """Convert to Claude tool use format.

        Returns:
            Tool definition in Claude API format.
        """
        properties = {}
        for name, param in self.parameters.items():
            prop: dict[str, Any] = {
                "type": param.type,
                "description": param.description,
            }
            if param.enum:
                prop["enum"] = param.enum
            properties[name] = prop

        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": self.required_parameters,
            },
        }
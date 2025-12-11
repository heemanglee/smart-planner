"""Tool registry for managing and executing tools."""

from typing import Any

from app.tools.base import BaseTool


class ToolRegistry:
    """Registry for managing tools."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool.

        Args:
            tool: Tool instance to register.
        """
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        """Get a tool by name.

        Args:
            name: Tool name.

        Returns:
            Tool instance or None if not found.
        """
        return self._tools.get(name)

    def list_tools(self) -> list[BaseTool]:
        """List all registered tools.

        Returns:
            List of all registered tools.
        """
        return list(self._tools.values())

    def get_tool_names(self) -> list[str]:
        """Get all tool names.

        Returns:
            List of tool names.
        """
        return list(self._tools.keys())

    def to_claude_tools(self) -> list[dict[str, Any]]:
        """Convert all tools to Claude tool use format.

        Returns:
            List of tool definitions in Claude API format.
        """
        return [tool.to_claude_tool() for tool in self._tools.values()]

    async def execute(self, name: str, **kwargs: Any) -> dict[str, Any]:
        """Execute a tool by name.

        Args:
            name: Tool name.
            **kwargs: Tool parameters.

        Returns:
            Tool execution result.

        Raises:
            ValueError: If tool not found.
        """
        tool = self.get(name)
        if tool is None:
            raise ValueError(f"Tool not found: {name}")
        return await tool.execute(**kwargs)


# Global registry instance
registry = ToolRegistry()
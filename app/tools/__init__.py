"""Tools module."""

from app.tools.base import BaseTool, ToolParameter
from app.tools.calendar import GetCalendarAvailabilityTool
from app.tools.registry import ToolRegistry, registry
from app.tools.weather import GetWeatherForecastTool
from app.tools.web_search import WebSearchTool

# Register all tools
registry.register(GetCalendarAvailabilityTool())
registry.register(GetWeatherForecastTool())
registry.register(WebSearchTool())

__all__ = [
    "BaseTool",
    "ToolParameter",
    "ToolRegistry",
    "registry",
    "GetCalendarAvailabilityTool",
    "GetWeatherForecastTool",
    "WebSearchTool",
]
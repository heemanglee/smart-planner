"""Tavily web search tool."""

from typing import Any

from tavily import TavilyClient

from app.config import settings
from app.tools.base import BaseTool, ToolParameter


class WebSearchTool(BaseTool):
    """Tool for web search using Tavily API."""

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return (
            "Search the web for information about events, places, activities, "
            "recommendations, and other relevant information for planning. "
            "Use this to find local events, restaurant recommendations, "
            "tourist attractions, and more."
        )

    @property
    def parameters(self) -> dict[str, ToolParameter]:
        return {
            "query": ToolParameter(
                type="string",
                description="Search query",
            ),
            "search_depth": ToolParameter(
                type="string",
                description="Search depth - 'basic' for quick search, 'advanced' for comprehensive",
                enum=["basic", "advanced"],
                default="basic",
            ),
            "max_results": ToolParameter(
                type="integer",
                description="Maximum number of results to return (1-10)",
                default="5",
            ),
        }

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        """Execute web search.

        Args:
            query: Search query.
            search_depth: basic or advanced.
            max_results: Number of results.

        Returns:
            Search results.
        """
        query = kwargs["query"]
        search_depth = kwargs.get("search_depth", "basic")
        max_results = int(kwargs.get("max_results", 5))

        if not settings.tavily_api_key:
            return {
                "success": False,
                "error": "Tavily API key not configured",
            }

        try:
            client = TavilyClient(api_key=settings.tavily_api_key)

            response = client.search(
                query=query,
                search_depth=search_depth,
                max_results=min(max_results, 10),
            )

            results = []
            for result in response.get("results", []):
                results.append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "content": result.get("content", ""),
                    "score": result.get("score", 0),
                })

            return {
                "success": True,
                "query": query,
                "results": results,
                "answer": response.get("answer", ""),
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "results": [],
            }
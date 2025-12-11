"""ReAct agent implementation."""

import json
from collections.abc import AsyncGenerator
from datetime import date
from typing import Any

import anthropic

from app.agent.prompts import get_system_prompt_with_context
from app.agent.types import (
    AgentResponse,
    AgentState,
    StreamEvent,
    ToolCallRequest,
    ToolResult,
)
from app.config import settings
from app.tools import registry


class ReActAgent:
    """ReAct agent using Claude API."""

    def __init__(
        self,
        max_iterations: int = 10,
        model: str | None = None,
    ) -> None:
        """Initialize the agent.

        Args:
            max_iterations: Maximum tool use iterations.
            model: Model to use (defaults to settings).
        """
        self.max_iterations = max_iterations
        self.model = model or settings.anthropic_model
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    async def run(
        self,
        messages: list[dict[str, Any]],
    ) -> AgentResponse:
        """Run the agent with given messages.

        Args:
            messages: Conversation messages.

        Returns:
            Agent response.
        """
        system_prompt = get_system_prompt_with_context(date.today().isoformat())
        tools = registry.to_claude_tools()

        all_tool_calls: list[ToolCallRequest] = []
        all_tool_results: list[ToolResult] = []
        total_tokens = 0

        current_messages = list(messages)

        for _ in range(self.max_iterations):
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
                tools=tools,
                messages=current_messages,
            )

            total_tokens += response.usage.input_tokens + response.usage.output_tokens

            # Check stop reason
            if response.stop_reason == "end_turn":
                # Extract text content
                content = ""
                for block in response.content:
                    if block.type == "text":
                        content = block.text
                        break

                return AgentResponse(
                    content=content,
                    tool_calls=all_tool_calls,
                    tool_results=all_tool_results,
                    state=AgentState.COMPLETED,
                    tokens_used=total_tokens,
                )

            elif response.stop_reason == "tool_use":
                # Process tool calls
                assistant_content = []
                tool_calls_in_turn: list[ToolCallRequest] = []

                for block in response.content:
                    if block.type == "text":
                        assistant_content.append({
                            "type": "text",
                            "text": block.text,
                        })
                    elif block.type == "tool_use":
                        tool_call = ToolCallRequest(
                            id=block.id,
                            name=block.name,
                            input=block.input,
                        )
                        tool_calls_in_turn.append(tool_call)
                        all_tool_calls.append(tool_call)
                        assistant_content.append({
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": block.input,
                        })

                # Add assistant message
                current_messages.append({
                    "role": "assistant",
                    "content": assistant_content,
                })

                # Execute tools and collect results
                tool_results_content = []
                for tool_call in tool_calls_in_turn:
                    result = await self._execute_tool(tool_call)
                    all_tool_results.append(result)
                    tool_results_content.append({
                        "type": "tool_result",
                        "tool_use_id": result.tool_use_id,
                        "content": result.content,
                        "is_error": result.is_error,
                    })

                # Add tool results
                current_messages.append({
                    "role": "user",
                    "content": tool_results_content,
                })

        # Max iterations reached
        return AgentResponse(
            content="I apologize, but I reached the maximum number of steps. Please try simplifying your request.",
            tool_calls=all_tool_calls,
            tool_results=all_tool_results,
            state=AgentState.ERROR,
            tokens_used=total_tokens,
        )

    async def run_stream(
        self,
        messages: list[dict[str, Any]],
    ) -> AsyncGenerator[StreamEvent, None]:
        """Run the agent with streaming.

        Args:
            messages: Conversation messages.

        Yields:
            Stream events.
        """
        system_prompt = get_system_prompt_with_context(date.today().isoformat())
        tools = registry.to_claude_tools()

        current_messages = list(messages)

        for iteration in range(self.max_iterations):
            yield StreamEvent(
                event_type="state",
                state=AgentState.THINKING,
            )

            # Stream response
            tool_calls_in_turn: list[ToolCallRequest] = []
            assistant_content: list[dict] = []
            current_text = ""
            current_tool_use: dict | None = None

            with self.client.messages.stream(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
                tools=tools,
                messages=current_messages,
            ) as stream:
                for event in stream:
                    if event.type == "content_block_start":
                        if event.content_block.type == "text":
                            current_text = ""
                        elif event.content_block.type == "tool_use":
                            current_tool_use = {
                                "id": event.content_block.id,
                                "name": event.content_block.name,
                                "input": "",
                            }

                    elif event.type == "content_block_delta":
                        if event.delta.type == "text_delta":
                            current_text += event.delta.text
                            yield StreamEvent(
                                event_type="text_delta",
                                content=event.delta.text,
                                state=AgentState.RESPONDING,
                            )
                        elif event.delta.type == "input_json_delta":
                            if current_tool_use:
                                current_tool_use["input"] += event.delta.partial_json

                    elif event.type == "content_block_stop":
                        if current_text:
                            assistant_content.append({
                                "type": "text",
                                "text": current_text,
                            })
                            current_text = ""
                        elif current_tool_use:
                            try:
                                input_data = json.loads(current_tool_use["input"])
                            except json.JSONDecodeError:
                                input_data = {}

                            tool_call = ToolCallRequest(
                                id=current_tool_use["id"],
                                name=current_tool_use["name"],
                                input=input_data,
                            )
                            tool_calls_in_turn.append(tool_call)
                            assistant_content.append({
                                "type": "tool_use",
                                "id": tool_call.id,
                                "name": tool_call.name,
                                "input": tool_call.input,
                            })

                            yield StreamEvent(
                                event_type="tool_use",
                                tool_call=tool_call,
                                state=AgentState.EXECUTING_TOOL,
                            )
                            current_tool_use = None

                response = stream.get_final_message()

            # Check if we're done
            if response.stop_reason == "end_turn":
                yield StreamEvent(
                    event_type="done",
                    state=AgentState.COMPLETED,
                )
                return

            # Process tool calls
            if tool_calls_in_turn:
                current_messages.append({
                    "role": "assistant",
                    "content": assistant_content,
                })

                tool_results_content = []
                for tool_call in tool_calls_in_turn:
                    result = await self._execute_tool(tool_call)
                    tool_results_content.append({
                        "type": "tool_result",
                        "tool_use_id": result.tool_use_id,
                        "content": result.content,
                        "is_error": result.is_error,
                    })

                    yield StreamEvent(
                        event_type="tool_result",
                        tool_result=result,
                        state=AgentState.THINKING,
                    )

                current_messages.append({
                    "role": "user",
                    "content": tool_results_content,
                })

        # Max iterations reached
        yield StreamEvent(
            event_type="error",
            content="Maximum iterations reached",
            state=AgentState.ERROR,
        )

    async def _execute_tool(self, tool_call: ToolCallRequest) -> ToolResult:
        """Execute a tool call.

        Args:
            tool_call: Tool call request.

        Returns:
            Tool execution result.
        """
        try:
            result = await registry.execute(tool_call.name, **tool_call.input)
            return ToolResult(
                tool_use_id=tool_call.id,
                content=json.dumps(result, ensure_ascii=False),
                is_error=not result.get("success", True),
            )
        except Exception as e:
            return ToolResult(
                tool_use_id=tool_call.id,
                content=json.dumps({"error": str(e)}),
                is_error=True,
            )
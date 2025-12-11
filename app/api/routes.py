"""API routes."""

import asyncio
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.agent import ReActAgent, AgentState
from app.api.schemas import (
    ChatRequest,
    ErrorResponse,
    MessageResponse,
    SessionCreate,
    SessionDetailResponse,
    SessionListResponse,
    SessionResponse,
    ToolCallResponse,
    ToolListResponse,
    ToolParameterResponse,
    ToolResponse,
)
from app.session import Message, SessionManager, generate_title
from app.tools import registry

router = APIRouter(prefix="/api", tags=["api"])

# Initialize session manager
session_manager = SessionManager()


# Session endpoints
@router.post(
    "/sessions",
    response_model=SessionResponse,
    responses={500: {"model": ErrorResponse}},
)
async def create_session(request: SessionCreate) -> SessionResponse:
    """Create a new session."""
    try:
        session = session_manager.create_session(title=request.title)
        return SessionResponse(
            id=session.id,
            title=session.title,
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=len(session.messages),
            total_tokens=session.total_tokens,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/sessions",
    response_model=SessionListResponse,
    responses={500: {"model": ErrorResponse}},
)
async def list_sessions(limit: int = 50) -> SessionListResponse:
    """List all sessions."""
    try:
        sessions = session_manager.list_sessions(limit=limit)
        return SessionListResponse(
            sessions=[
                SessionResponse(
                    id=s.id,
                    title=s.title,
                    created_at=s.created_at,
                    updated_at=s.updated_at,
                    message_count=len(s.messages),
                    total_tokens=s.total_tokens,
                )
                for s in sessions
            ],
            total=len(sessions),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/sessions/{session_id}",
    response_model=SessionDetailResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def get_session(session_id: str) -> SessionDetailResponse:
    """Get session details."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionDetailResponse(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages=[
            MessageResponse(
                role=m.role,
                content=m.content,
                timestamp=m.timestamp,
                tool_calls=[
                    ToolCallResponse(
                        id=tc.id,
                        name=tc.name,
                        input=tc.input,
                        result=tc.result,
                    )
                    for tc in m.tool_calls
                ],
            )
            for m in session.messages
        ],
        total_tokens=session.total_tokens,
    )


@router.delete(
    "/sessions/{session_id}",
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def delete_session(session_id: str) -> dict:
    """Delete a session."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session_manager.delete_session(session_id):
        raise HTTPException(status_code=500, detail="Failed to delete session")

    return {"message": "Session deleted"}


# Chat endpoint
@router.post(
    "/sessions/{session_id}/chat",
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def chat(session_id: str, request: ChatRequest) -> StreamingResponse:
    """Chat with the agent (SSE streaming)."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    async def event_generator():
        try:
            # Add user message
            user_message = Message(role="user", content=request.message)
            session_manager.add_message(session_id, user_message)

            # Generate title for first message
            if len(session.messages) == 0:
                title = await generate_title(request.message)
                session_manager.update_title(session_id, title)
                yield f"event: title\ndata: {json.dumps({'title': title})}\n\n"

            # Get conversation history
            messages = [
                {"role": m.role, "content": m.content}
                for m in session_manager.get_messages(session_id)
                if m.role in ("user", "assistant")
            ]

            # Run agent
            agent = ReActAgent()
            full_response = ""

            async for event in agent.run_stream(messages):
                if event.event_type == "text_delta":
                    full_response += event.content
                    yield f"event: text\ndata: {json.dumps({'content': event.content})}\n\n"

                elif event.event_type == "tool_use":
                    yield f"event: tool_use\ndata: {json.dumps({'name': event.tool_call.name, 'input': event.tool_call.input})}\n\n"

                elif event.event_type == "tool_result":
                    result_data = json.loads(event.tool_result.content)
                    yield f"event: tool_result\ndata: {json.dumps({'tool_use_id': event.tool_result.tool_use_id, 'result': result_data})}\n\n"

                elif event.event_type == "done":
                    # Save assistant message
                    if full_response:
                        assistant_message = Message(
                            role="assistant",
                            content=full_response,
                        )
                        session_manager.add_message(session_id, assistant_message)

                    yield f"event: done\ndata: {json.dumps({'status': 'completed'})}\n\n"

                elif event.event_type == "error":
                    yield f"event: error\ndata: {json.dumps({'error': event.content})}\n\n"

                # Small delay for streaming
                await asyncio.sleep(0.01)

        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# Tools endpoint
@router.get(
    "/tools",
    response_model=ToolListResponse,
)
async def list_tools() -> ToolListResponse:
    """List all available tools."""
    tools = []
    for tool in registry.list_tools():
        params = {}
        for name, param in tool.parameters.items():
            params[name] = ToolParameterResponse(
                type=param.type,
                description=param.description,
                enum=param.enum,
                required=param.default is None,
            )
        tools.append(
            ToolResponse(
                name=tool.name,
                description=tool.description,
                parameters=params,
            )
        )
    return ToolListResponse(tools=tools)
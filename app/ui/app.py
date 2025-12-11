"""Streamlit UI for SkyPlanner."""

import json

import requests
import streamlit as st

API_BASE_URL = "http://localhost:8001/api"


def init_session_state():
    """Initialize session state."""
    if "current_session_id" not in st.session_state:
        st.session_state.current_session_id = None
    if "messages" not in st.session_state:
        st.session_state.messages = []


def fetch_sessions():
    """Fetch all sessions from API."""
    try:
        response = requests.get(f"{API_BASE_URL}/sessions", timeout=10)
        response.raise_for_status()
        return response.json()["sessions"]
    except Exception:
        return []


def create_session():
    """Create a new session."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/sessions",
            json={"title": "New Session"},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


def delete_session(session_id: str):
    """Delete a session."""
    try:
        response = requests.delete(
            f"{API_BASE_URL}/sessions/{session_id}",
            timeout=10,
        )
        response.raise_for_status()
        return True
    except Exception:
        return False


def fetch_session_detail(session_id: str):
    """Fetch session detail."""
    try:
        response = requests.get(
            f"{API_BASE_URL}/sessions/{session_id}",
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


def stream_chat(session_id: str, message: str):
    """Stream chat response."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/sessions/{session_id}/chat",
            json={"message": message},
            stream=True,
            timeout=120,
        )
        response.raise_for_status()

        for line in response.iter_lines():
            if line:
                line = line.decode("utf-8")
                if line.startswith("event:"):
                    event_type = line.split(":", 1)[1].strip()
                elif line.startswith("data:"):
                    data = json.loads(line.split(":", 1)[1].strip())
                    yield event_type, data
    except Exception as e:
        yield "error", {"error": str(e)}


def render_sidebar():
    """Render sidebar with session list."""
    with st.sidebar:
        st.title("SkyPlanner")
        st.caption("Weather & Schedule Assistant")

        st.divider()

        # New session button
        if st.button("+ New Session", use_container_width=True):
            session = create_session()
            if session:
                st.session_state.current_session_id = session["id"]
                st.session_state.messages = []
                st.rerun()

        st.divider()

        # Session list
        st.subheader("Sessions")
        sessions = fetch_sessions()

        for session in sessions:
            col1, col2 = st.columns([4, 1])

            with col1:
                is_current = session["id"] == st.session_state.current_session_id
                if st.button(
                    session["title"][:30] + ("..." if len(session["title"]) > 30 else ""),
                    key=f"session_{session['id']}",
                    use_container_width=True,
                    type="primary" if is_current else "secondary",
                ):
                    st.session_state.current_session_id = session["id"]
                    # Load messages
                    detail = fetch_session_detail(session["id"])
                    if detail:
                        st.session_state.messages = [
                            {"role": m["role"], "content": m["content"]}
                            for m in detail["messages"]
                        ]
                    st.rerun()

            with col2:
                if st.button("🗑️", key=f"delete_{session['id']}"):
                    if delete_session(session["id"]):
                        if st.session_state.current_session_id == session["id"]:
                            st.session_state.current_session_id = None
                            st.session_state.messages = []
                        st.rerun()


def render_chat():
    """Render chat interface."""
    if not st.session_state.current_session_id:
        st.info("Select a session or create a new one to start chatting.")
        return

    # Display messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Ask about weather, schedules, or planning..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Stream assistant response
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            tool_container = st.container()

            full_response = ""
            tool_calls = []

            for event_type, data in stream_chat(
                st.session_state.current_session_id, prompt
            ):
                if event_type == "title":
                    # Session title updated
                    pass

                elif event_type == "text":
                    full_response += data.get("content", "")
                    response_placeholder.markdown(full_response + "▌")

                elif event_type == "tool_use":
                    tool_name = data.get("name", "Unknown")
                    tool_input = data.get("input", {})
                    tool_calls.append({"name": tool_name, "input": tool_input})

                    with tool_container:
                        with st.expander(f"🔧 Using tool: {tool_name}", expanded=False):
                            st.json(tool_input)

                elif event_type == "tool_result":
                    result = data.get("result", {})
                    if tool_calls:
                        with tool_container:
                            with st.expander(
                                f"📊 Result from: {tool_calls[-1]['name']}",
                                expanded=False,
                            ):
                                st.json(result)

                elif event_type == "done":
                    response_placeholder.markdown(full_response)

                elif event_type == "error":
                    st.error(f"Error: {data.get('error', 'Unknown error')}")

            # Add assistant message to history
            if full_response:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": full_response,
                })


def main():
    """Main entry point."""
    st.set_page_config(
        page_title="SkyPlanner",
        page_icon="🌤️",
        layout="wide",
    )

    init_session_state()
    render_sidebar()
    render_chat()


if __name__ == "__main__":
    main()
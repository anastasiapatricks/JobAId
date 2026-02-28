"""Dependency injection for FastAPI — session store, graph instance."""

import uuid
from typing import Dict, Any
from graph.builder import build_graph
from agents.orchestrator import reset_autonomy

# In-memory session store (dict) — interface abstracted for future Redis/DB swap
_sessions: Dict[str, Dict[str, Any]] = {}

# Compiled graph (singleton)
_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def create_session(initial_data: Dict[str, Any] | None = None) -> str:
    """Create a new session and return its ID."""
    session_id = str(uuid.uuid4())
    state = initial_data or {}
    state.setdefault("results", [])
    _sessions[session_id] = {
        "session_id": session_id,
        "status": "created",
        "state": state,
        "result": None,
    }
    return session_id


def get_session(session_id: str) -> Dict[str, Any] | None:
    return _sessions.get(session_id)


def update_session(session_id: str, **kwargs):
    if session_id in _sessions:
        _sessions[session_id].update(kwargs)


def delete_session(session_id: str) -> bool:
    return _sessions.pop(session_id, None) is not None


def list_sessions() -> list:
    return [
        {"session_id": s["session_id"], "status": s["status"]}
        for s in _sessions.values()
    ]

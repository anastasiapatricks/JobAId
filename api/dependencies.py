"""Dependency injection for FastAPI — session store, graph instance."""

import json
import uuid
import logging
from typing import Dict, Any
from datetime import datetime, timezone
from graph.builder import build_graph
from agents.orchestrator import reset_autonomy

# In-memory session store (dict) — interface abstracted for future Redis/DB swap
_sessions: Dict[str, Dict[str, Any]] = {}

# Compiled graph (singleton)
_graph = None

_session_logger = logging.getLogger("jobaid.session")


def _log_session_event(action: str, session_id: str, new_status: str):
    _session_logger.info(json.dumps({
        "event": "session_lifecycle",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "session_id": session_id,
        "new_status": new_status,
    }))


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
    _log_session_event("create", session_id, "created")
    return session_id


def get_session(session_id: str) -> Dict[str, Any] | None:
    return _sessions.get(session_id)


def update_session(session_id: str, **kwargs):
    if session_id in _sessions:
        _sessions[session_id].update(kwargs)
        new_status = kwargs.get("status", _sessions[session_id].get("status", "unknown"))
        _log_session_event("update", session_id, new_status)


def delete_session(session_id: str) -> bool:
    removed = _sessions.pop(session_id, None) is not None
    if removed:
        _log_session_event("delete", session_id, "deleted")
    return removed


def list_sessions() -> list:
    return [
        {"session_id": s["session_id"], "status": s["status"]}
        for s in _sessions.values()
    ]

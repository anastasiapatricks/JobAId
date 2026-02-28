"""Dependency injection for FastAPI — session store, graph instance."""

import json
import uuid
import logging
import threading
from typing import Dict, Any
from datetime import datetime, timezone
from graph.builder import build_graph
from agents.orchestrator import reset_autonomy

SESSION_TTL_SECONDS = 3600  # 1 hour

# In-memory session store (dict) — interface abstracted for future Redis/DB swap
_sessions: Dict[str, Dict[str, Any]] = {}
_reaper_started = False

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


def _reap_expired_sessions():
    """Remove sessions older than SESSION_TTL_SECONDS. Runs every 60s."""
    now = datetime.now(timezone.utc)
    expired = [
        sid for sid, s in _sessions.items()
        if (now - s["created_at"]).total_seconds() > SESSION_TTL_SECONDS
    ]
    for sid in expired:
        _sessions.pop(sid, None)
        _log_session_event("evict", sid, "expired")
    # Schedule next run
    timer = threading.Timer(60, _reap_expired_sessions)
    timer.daemon = True
    timer.start()


def start_session_reaper():
    """Start the background reaper thread (called once at app startup)."""
    global _reaper_started
    if not _reaper_started:
        _reaper_started = True
        _reap_expired_sessions()


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
        "created_at": datetime.now(timezone.utc),
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

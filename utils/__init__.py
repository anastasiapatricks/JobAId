import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any

_debug_logger = logging.getLogger("jobaid.debug")


def _log_context() -> dict:
    """Return session_id and request_id from contextvars for log correlation.

    Safe to call from any thread — returns empty values if context is not set.
    """
    ctx: dict = {}
    try:
        from api.middleware import current_session_id, current_request_id
        sid = current_session_id.get()
        rid = current_request_id.get()
        if sid:
            ctx["session_id"] = sid
        if rid:
            ctx["request_id"] = rid
    except Exception:
        pass
    # Fallback: check llm_logger's local session_id (set in background threads)
    if "session_id" not in ctx:
        try:
            from utils.llm_logger import _session_id_var
            sid = _session_id_var.get()
            if sid:
                ctx["session_id"] = sid
        except Exception:
            pass
    return ctx


def get_latest_results(state: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten the results array into a dict with the latest value per field.

    Iterates through all entries in state["results"] and returns a dict
    containing the most recent value for each field (excluding 'action' and 'timestamp').
    """
    flat: Dict[str, Any] = {}
    for entry in state.get("results", []):
        for k, v in entry.items():
            if k not in ("action", "timestamp"):
                flat[k] = v
    return flat


def debug(message, prefix="DEBUG"):
    """Log debug message via logging framework (always) and print colored output when DEBUG=true."""
    entry = {
        "event": "debug",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prefix": prefix,
        "message": str(message),
        **_log_context(),
    }
    _debug_logger.info(json.dumps(entry))

    if os.getenv("DEBUG", "false").lower() == "true":
        print(f"    \033[2m[{prefix}] {message}\033[0m")

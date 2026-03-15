"""Structured LLM call logging for observability."""

import json
import time
import logging
import contextvars
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("jobaid.llm")

# Context var for session_id — set by middleware or explicitly in background threads
_session_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "llm_session_id", default=None
)


def set_session_id(session_id: str) -> None:
    """Set session_id for the current context (call from background threads)."""
    _session_id_var.set(session_id)


def _get_session_id() -> str | None:
    """Get session_id from local contextvar or middleware contextvar."""
    sid = _session_id_var.get()
    if sid:
        return sid
    # Fallback to middleware contextvar
    try:
        from api.middleware import current_session_id
        return current_session_id.get()
    except Exception:
        return None


class LLMCallLogger:
    """Tracks and logs LLM invocations per session."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.total_calls = 0
        self.total_tokens = 0
        self.total_latency = 0.0

    def log_call(
        self,
        model: str,
        task_type: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        latency_ms: float = 0.0,
        error: Optional[str] = None,
    ):
        """Log a single LLM call with structured JSON."""
        self.total_calls += 1
        self.total_tokens += prompt_tokens + completion_tokens
        self.total_latency += latency_ms

        entry = {
            "event": "llm_call",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": self.session_id,
            "model": model,
            "task_type": task_type,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "latency_ms": round(latency_ms, 1),
        }

        if error:
            entry["error"] = error
            logger.error(json.dumps(entry))
        else:
            logger.info(json.dumps(entry))

    def log_session_summary(self):
        """Log aggregate stats for the session."""
        entry = {
            "event": "llm_session_summary",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": self.session_id,
            "total_calls": self.total_calls,
            "total_tokens": self.total_tokens,
            "total_latency_ms": round(self.total_latency, 1),
            "avg_latency_ms": round(self.total_latency / max(self.total_calls, 1), 1),
        }
        logger.info(json.dumps(entry))


def logged_invoke(llm, messages, task_type: str):
    """Invoke an LLM and log the call with timing and token usage.

    Drop-in replacement for llm.invoke(messages) — returns the same response object.
    """
    session_id = _get_session_id()
    start = time.time()
    try:
        response = llm.invoke(messages)
        latency = (time.time() - start) * 1000
        usage = response.usage_metadata or {}
        entry = {
            "event": "llm_call",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": llm.model_name,
            "task_type": task_type,
            "prompt_tokens": usage.get("input_tokens", 0),
            "completion_tokens": usage.get("output_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "latency_ms": round(latency, 1),
            "status": "success",
        }
        if session_id:
            entry["session_id"] = session_id
        logger.info(json.dumps(entry))
        return response
    except Exception as e:
        latency = (time.time() - start) * 1000
        entry = {
            "event": "llm_call",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": getattr(llm, "model_name", "unknown"),
            "task_type": task_type,
            "latency_ms": round(latency, 1),
            "status": "error",
            "error": str(e)[:200],
        }
        if session_id:
            entry["session_id"] = session_id
        logger.error(json.dumps(entry))
        raise

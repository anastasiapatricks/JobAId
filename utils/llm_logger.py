"""Structured LLM call logging for observability."""

import json
import time
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("jobaid.llm")


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


def timed_llm_call(func):
    """Decorator to time and log LLM calls."""
    def wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = func(*args, **kwargs)
            latency = (time.time() - start) * 1000
            logger.info(json.dumps({
                "event": "llm_call",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "function": func.__name__,
                "latency_ms": round(latency, 1),
                "status": "success",
            }))
            return result
        except Exception as e:
            latency = (time.time() - start) * 1000
            logger.error(json.dumps({
                "event": "llm_call",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "function": func.__name__,
                "latency_ms": round(latency, 1),
                "status": "error",
                "error": str(e)[:200],
            }))
            raise
    return wrapper

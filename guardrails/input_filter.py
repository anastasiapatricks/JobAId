"""Input validation and prompt injection defense."""

import json
import re
import logging
from typing import Tuple
from datetime import datetime, timezone

_guard_logger = logging.getLogger("jobaid.guardrails")

# Patterns that suggest prompt injection attempts
_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|above|prior)\s+(instructions|prompts)", re.I),
    re.compile(r"you\s+are\s+now\s+", re.I),
    re.compile(r"system\s*:\s*", re.I),
    re.compile(r"<\s*/?\s*system\s*>", re.I),
    re.compile(r"ADMIN\s*MODE", re.I),
    re.compile(r"jailbreak", re.I),
    re.compile(r"DAN\s+mode", re.I),
]

MAX_INPUT_LENGTH = 50_000  # 50KB max for resume text
MAX_QUERY_LENGTH = 500


def validate_resume_text(text: str) -> Tuple[bool, str]:
    """Validate resume text input. Returns (is_valid, error_message)."""
    if not text or not text.strip():
        return False, "Resume text is empty."
    if len(text) > MAX_INPUT_LENGTH:
        return False, f"Resume text exceeds maximum length ({MAX_INPUT_LENGTH} chars)."
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            _guard_logger.warning(json.dumps({
                "event": "guardrail_triggered",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "guardrail": "prompt_injection",
                "stage": "resume_input",
                "detail": f"matched pattern: {pattern.pattern[:60]}",
            }))
            return False, "Input contains suspicious patterns and was rejected."
    return True, ""


def validate_job_query(query: str) -> Tuple[bool, str]:
    """Validate job search query. Returns (is_valid, error_message)."""
    if not query or not query.strip():
        return False, "Job query is empty."
    if len(query) > MAX_QUERY_LENGTH:
        return False, f"Job query exceeds maximum length ({MAX_QUERY_LENGTH} chars)."
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(query):
            _guard_logger.warning(json.dumps({
                "event": "guardrail_triggered",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "guardrail": "prompt_injection",
                "stage": "job_query_input",
                "detail": f"matched pattern: {pattern.pattern[:60]}",
            }))
            return False, "Input contains suspicious patterns and was rejected."
    return True, ""


def spotlight_wrap(user_input: str) -> str:
    """Wrap user input with delimiter spotlighting to prevent injection."""
    return f"<<<USER_INPUT>>>\n{user_input}\n<<<END_USER_INPUT>>>"

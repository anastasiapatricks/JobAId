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

# Content safety: harmful/illegal/unethical job request patterns
_UNSAFE_JOB_PATTERNS = [
    # Violence and crime
    re.compile(r"\b(hitman|assassin|hit\s*man|contract\s*kill(er|ing)?|murder\s*for\s*hire)\b", re.I),
    re.compile(r"\b(robbery|robber|burglar|burglary|heist)\s*(job|work|position|opportunit)", re.I),
    re.compile(r"\b(drug\s*(dealer|trafficking|smuggl)|narcotic|cartel)\b", re.I),
    re.compile(r"\b(human\s*traffick\w*|sex\s*traffick\w*|smuggl\w*\s*people|traffick\w*\s*(people|human|person))\b", re.I),
    re.compile(r"\b(kidnap\w*|ransom|extortion|blackmail)\s*(job|work|for\s*(hire|money))?", re.I),
    re.compile(r"\b(terrorism|terrorist|bomb\s*mak|weapon\s*smuggl)\b", re.I),
    re.compile(r"\b(arson|arsonist)\b", re.I),
    # Fraud and scams
    re.compile(r"\b(scam\s*(artist|job|people)|fraud\s*scheme|ponzi|pyramid\s*scheme)\b", re.I),
    re.compile(r"\b(money\s*launder\w*|counterfeit\w*|forg(e|ing)\s*(document|passport|id))\b", re.I),
    re.compile(r"\b(identity\s*theft|steal\s*(identity|credit\s*card|data))\b", re.I),
    # Exploitation
    re.compile(r"\b(child\s*(exploit\w*|labour|labor|porn\w*|abuse))\b", re.I),
    re.compile(r"\b(sweatshop|forced\s*labour|slave\s*labour)\b", re.I),
    # Illegal hacking (distinct from legitimate cybersecurity)
    re.compile(r"\b(hack\s*(into|bank|account|someone)|black\s*hat\s*hack)\b", re.I),
    re.compile(r"\b(steal\s*(password|credentials|money|crypto)s?)\b", re.I),
]

_UNSAFE_RESPONSE = (
    "I can only help with legitimate job searches. "
    "Your request appears to describe illegal or harmful activities. "
    "Please try a different search, such as a specific job title or industry."
)


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
    # Content safety: block harmful/illegal job requests
    for pattern in _UNSAFE_JOB_PATTERNS:
        if pattern.search(query):
            _guard_logger.warning(json.dumps({
                "event": "guardrail_triggered",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "guardrail": "content_safety",
                "stage": "job_query_input",
                "detail": f"unsafe job request: {pattern.pattern[:60]}",
            }))
            return False, _UNSAFE_RESPONSE
    return True, ""


def validate_chat_message(message: str) -> Tuple[bool, str]:
    """Validate a conversational chat message for content safety.

    Returns (is_valid, error_message). Unlike job query validation,
    this only checks for content safety (not injection, since the
    orchestrator handles spotlight wrapping).
    """
    if not message or not message.strip():
        return True, ""  # Empty messages are handled by the orchestrator
    for pattern in _UNSAFE_JOB_PATTERNS:
        if pattern.search(message):
            _guard_logger.warning(json.dumps({
                "event": "guardrail_triggered",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "guardrail": "content_safety",
                "stage": "chat_message",
                "detail": f"unsafe request: {pattern.pattern[:60]}",
            }))
            return False, _UNSAFE_RESPONSE
    return True, ""


def spotlight_wrap(user_input: str) -> str:
    """Wrap user input with delimiter spotlighting to prevent injection."""
    return f"<<<USER_INPUT>>>\n{user_input}\n<<<END_USER_INPUT>>>"

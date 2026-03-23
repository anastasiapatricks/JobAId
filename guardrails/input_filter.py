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


# ─── Indirect prompt injection defense for pitch generator ───
# These patterns target injection attempts that arrive via external data
# (job listings from APIs, web search results, Wikipedia) rather than
# direct user input.

_INDIRECT_INJECTION_PATTERNS = [
    # Core injection attempts (superset of _INJECTION_PATTERNS, tuned for external text)
    *_INJECTION_PATTERNS,
    # System prompt extraction
    re.compile(r"(output|reveal|show|print|repeat|display)\s+(the\s+|your\s+)?(system\s+prompt|instructions|system\s+message)", re.I),
    re.compile(r"what\s+(are|is)\s+(your|the)\s+(system\s+)?(instructions|prompt|rules)", re.I),
    # Role hijacking via external content
    re.compile(r"(forget|disregard|override)\s+(everything|all|your)\s+(above|previous|instructions|rules)?", re.I),
    re.compile(r"new\s+instructions?\s*:", re.I),
    re.compile(r"act\s+as\s+(if\s+you\s+are|a)\b", re.I),
    # Data exfiltration attempts
    re.compile(r"(send|forward|email|post|exfiltrate|transmit)\s+(this|the|all)\s+(data|info|conversation|context|resume)", re.I),
    re.compile(r"(curl|wget|fetch|request)\s+https?://", re.I),
    # Encoded/obfuscated injection
    re.compile(r"base64\s*(decode|encode)", re.I),
    re.compile(r"\\x[0-9a-f]{2}", re.I),
]

MAX_EXTERNAL_CONTENT_LENGTH = 10_000  # Max chars for external research content


def sanitize_pitch_input(
    text: str, source: str
) -> Tuple[str, bool, str]:
    """Sanitize external content before it enters the pitch generator LLM prompt.

    Scans job listing data, web search results, and Wikipedia content for
    indirect prompt injection attempts. Returns (sanitized_text, is_safe, detail).

    If injection is detected, the offending text is stripped and a warning is logged.
    The sanitized text is still returned (with injections removed) so the pipeline
    can continue with degraded but safe input.
    """
    if not text:
        return text, True, ""

    # Length cap — external content should not be excessively long
    if len(text) > MAX_EXTERNAL_CONTENT_LENGTH:
        text = text[:MAX_EXTERNAL_CONTENT_LENGTH]
        _guard_logger.info(json.dumps({
            "event": "guardrail_triggered",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "guardrail": "input_length_trim",
            "stage": f"pitch_input_{source}",
            "detail": f"trimmed to {MAX_EXTERNAL_CONTENT_LENGTH} chars",
        }))

    found_injections = []
    sanitized = text
    for pattern in _INDIRECT_INJECTION_PATTERNS:
        match = pattern.search(sanitized)
        if match:
            found_injections.append(pattern.pattern[:60])
            # Strip the offending segment rather than rejecting entirely
            sanitized = pattern.sub("[FILTERED]", sanitized)

    if found_injections:
        detail = f"indirect injection in {source}: {found_injections}"
        _guard_logger.warning(json.dumps({
            "event": "guardrail_triggered",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "guardrail": "indirect_prompt_injection",
            "stage": f"pitch_input_{source}",
            "detail": detail,
        }))
        return sanitized, False, detail

    return sanitized, True, ""


def validate_pitch_job_data(job: dict) -> Tuple[dict, bool, list]:
    """Validate and sanitize job listing data before pitch generation.

    Scans job title, company name, description, and keywords for injection
    patterns. Returns (sanitized_job, is_safe, list_of_warnings).
    """
    if not job or not isinstance(job, dict):
        return job, True, []

    warnings = []
    sanitized_job = dict(job)  # shallow copy

    for field in ("title", "company", "description", "location"):
        value = job.get(field, "")
        if not isinstance(value, str):
            continue
        cleaned, is_safe, detail = sanitize_pitch_input(value, f"job_{field}")
        if not is_safe:
            warnings.append(f"job.{field}: {detail}")
            sanitized_job[field] = cleaned

    # Sanitize keywords list
    keywords = job.get("keywords", [])
    if isinstance(keywords, list):
        clean_keywords = []
        for kw in keywords:
            if isinstance(kw, str):
                cleaned, is_safe, _ = sanitize_pitch_input(kw, "job_keyword")
                clean_keywords.append(cleaned)
        sanitized_job["keywords"] = clean_keywords

    return sanitized_job, len(warnings) == 0, warnings

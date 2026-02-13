"""PII detection and de-biasing for resume data."""

import re
from typing import Dict, Any


# Patterns that may reveal protected characteristics
_EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
_PHONE_RE = re.compile(r"[\+]?[\d\s\-().]{7,15}")
_GENDER_INDICATORS = {"mr", "ms", "mrs", "miss", "sir", "madam", "he", "she", "him", "her"}


def strip_pii(resume_info: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of resume_info with PII removed for downstream de-biased processing.

    Strips: name, email, phone, and gender indicators from summary text.
    Preserves: skills, experience descriptions, education, industry terms.
    """
    debiased = _deep_copy(resume_info)

    # Strip contact_info identifiers
    contact = debiased.get("contact_info", {})
    if isinstance(contact, dict):
        contact.pop("name", None)
        contact.pop("email", None)
        contact.pop("phone", None)
        debiased["contact_info"] = contact

    # Scrub summary for gender indicators
    summary = debiased.get("professional_summary", "")
    if summary:
        words = summary.split()
        words = [w for w in words if w.lower().strip(".,;:!?") not in _GENDER_INDICATORS]
        debiased["professional_summary"] = " ".join(words)

    return debiased


def sanitize_text(text: str) -> str:
    """Remove email addresses and phone numbers from raw text."""
    text = _EMAIL_RE.sub("[EMAIL]", text)
    text = _PHONE_RE.sub("[PHONE]", text)
    return text


def _deep_copy(obj):
    """Simple deep copy for dicts/lists without importing copy."""
    if isinstance(obj, dict):
        return {k: _deep_copy(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_deep_copy(i) for i in obj]
    return obj

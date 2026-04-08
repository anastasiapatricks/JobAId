"""PII detection and de-biasing for resume data."""

import re
from typing import Dict, Any, List, Tuple, Optional
import logging

_logger = logging.getLogger("jobaid.pii_sanitizer")

# Patterns that may reveal protected characteristics
_EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
_PHONE_RE = re.compile(r"\b(?:\+?\d{1,3}[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b")
_GENDER_INDICATORS = {"mr", "ms", "mrs", "miss", "sir", "madam", "he", "she", "him", "her"}

# Extended PII patterns
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")  # SSN format: 123-45-6789
_ZIP_RE = re.compile(r"\b\d{5}(?:-\d{4})?\b")  # US ZIP codes
_DATE_OF_BIRTH_RE = re.compile(
    r"\b(?:DOB|Date of Birth|Born)[:\s]*"
    r"(?:\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2}|"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})",
    re.I
)
_ADDRESS_RE = re.compile(
    r"\b\d+\s+(?:[A-Z][a-z]+\s+){1,3}(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Circle|Cir)\b",
    re.I
)
_LINKEDIN_RE = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[\w-]+/?", re.I)
_GITHUB_RE = re.compile(r"(?:https?://)?(?:www\.)?github\.com/[\w-]+/?", re.I)

# Try to load spaCy model, but don't fail if unavailable
_SPACY_MODEL: Optional[Any] = None
try:
    import spacy
    try:
        _SPACY_MODEL = spacy.load("en_core_web_sm")
        _logger.info("spaCy model loaded successfully for NER-based PII detection")
    except OSError:
        _logger.warning(
            "spaCy model 'en_core_web_sm' not found. Install with:\n"
            "  uv add spacy\n"
            "  uv sync\n"
            "  uv run python -m spacy download en_core_web_sm"
        )
except ImportError:
    _logger.warning(
        "spaCy not installed. NER-based PII detection disabled. Install with:\n"
        "  uv add spacy\n"
        "  uv sync\n"
        "  uv run python -m spacy download en_core_web_sm"
    )


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


def detect_pii_regex(text: str) -> List[Dict[str, Any]]:
    """Detect PII using regex patterns.

    Returns:
        List of detected entities with type, text, start, and end positions.
    """
    entities = []

    # Email addresses
    for match in _EMAIL_RE.finditer(text):
        entities.append({
            "type": "EMAIL",
            "text": match.group(),
            "start": match.start(),
            "end": match.end(),
        })

    # Phone numbers
    for match in _PHONE_RE.finditer(text):
        entities.append({
            "type": "PHONE",
            "text": match.group(),
            "start": match.start(),
            "end": match.end(),
        })

    # SSN
    for match in _SSN_RE.finditer(text):
        entities.append({
            "type": "SSN",
            "text": match.group(),
            "start": match.start(),
            "end": match.end(),
        })

    # ZIP codes
    for match in _ZIP_RE.finditer(text):
        entities.append({
            "type": "ZIP_CODE",
            "text": match.group(),
            "start": match.start(),
            "end": match.end(),
        })

    # Date of birth
    for match in _DATE_OF_BIRTH_RE.finditer(text):
        entities.append({
            "type": "DATE_OF_BIRTH",
            "text": match.group(),
            "start": match.start(),
            "end": match.end(),
        })

    # Street addresses
    for match in _ADDRESS_RE.finditer(text):
        entities.append({
            "type": "ADDRESS",
            "text": match.group(),
            "start": match.start(),
            "end": match.end(),
        })

    # LinkedIn profiles
    for match in _LINKEDIN_RE.finditer(text):
        entities.append({
            "type": "LINKEDIN_URL",
            "text": match.group(),
            "start": match.start(),
            "end": match.end(),
        })

    # GitHub profiles
    for match in _GITHUB_RE.finditer(text):
        entities.append({
            "type": "GITHUB_URL",
            "text": match.group(),
            "start": match.start(),
            "end": match.end(),
        })

    return entities


def detect_pii_ner(text: str) -> List[Dict[str, Any]]:
    """Detect PII using spaCy Named Entity Recognition.

    Returns:
        List of detected entities with type, text, start, and end positions.
        Returns empty list if spaCy is not available.
    """
    if _SPACY_MODEL is None:
        return []

    entities = []
    doc = _SPACY_MODEL(text)

    # Map spaCy entity types to PII categories.
    # Only PERSON names are redacted — ORG, GPE, LOC, DATE, NORP are all
    # critical resume content (employers, cities, work-period dates) and
    # stripping them degrades downstream parsing quality.
    pii_entity_types = {
        "PERSON",      # People names
    }

    for ent in doc.ents:
        if ent.label_ in pii_entity_types:
            entities.append({
                "type": f"NER_{ent.label_}",
                "text": ent.text,
                "start": ent.start_char,
                "end": ent.end_char,
                "label": ent.label_,
            })

    return entities


def detect_pii(text: str, use_ner: bool = True) -> List[Dict[str, Any]]:
    """Detect PII using both regex and spaCy NER.

    Args:
        text: Input text to scan for PII
        use_ner: Whether to use spaCy NER (default: True)

    Returns:
        Combined list of detected PII entities, sorted by position.
    """
    entities = detect_pii_regex(text)

    if use_ner:
        ner_entities = detect_pii_ner(text)
        entities.extend(ner_entities)

    # Remove duplicates by position and sort
    seen_positions = set()
    unique_entities = []
    for entity in sorted(entities, key=lambda e: e["start"]):
        pos_key = (entity["start"], entity["end"])
        if pos_key not in seen_positions:
            seen_positions.add(pos_key)
            unique_entities.append(entity)

    return unique_entities


def filter_pii(text: str, redact_char: str = "[REDACTED]", use_ner: bool = True) -> Tuple[str, List[Dict[str, Any]]]:
    """Remove or redact PII from text using comprehensive detection.

    Args:
        text: Input text to filter
        redact_char: Replacement string for PII (default: "[REDACTED]")
        use_ner: Whether to use spaCy NER (default: True)

    Returns:
        Tuple of (filtered_text, detected_entities)
    """
    entities = detect_pii(text, use_ner=use_ner)

    if not entities:
        return text, []

    # Sort entities by position in reverse order to maintain offsets
    entities_sorted = sorted(entities, key=lambda e: e["start"], reverse=True)

    filtered_text = text
    for entity in entities_sorted:
        # Replace entity text with redaction marker
        filtered_text = (
            filtered_text[:entity["start"]] +
            redact_char +
            filtered_text[entity["end"]:]
        )

    _logger.info(f"Filtered {len(entities)} PII entities from text")
    return filtered_text, entities


def _deep_copy(obj):
    """Simple deep copy for dicts/lists without importing copy."""
    if isinstance(obj, dict):
        return {k: _deep_copy(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_deep_copy(i) for i in obj]
    return obj

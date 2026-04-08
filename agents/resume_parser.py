"""LLM-powered resume parser with structured extraction and de-biasing."""

import json
import unicodedata
from typing import Dict, Any

from langchain_core.messages import SystemMessage, HumanMessage

import logging

from config.settings import settings
from config.prompts import RESUME_PARSER_SYSTEM, RESUME_PARSER_CONFIDENCE, RESUME_PARSER_PROMPT_VERSION
from xai.trace import create_trace
from guardrails.input_filter import spotlight_wrap, validate_resume_text
from guardrails.output_filter import validate_resume_output, scan_output_for_pii
from guardrails.model_router import get_model_for_task
from guardrails.llm_factory import get_llm
from tools.pii_sanitizer import strip_pii, filter_pii
from utils import debug
from utils.llm_logger import logged_invoke

_guard_logger = logging.getLogger("jobaid.guardrails")


def load_resume_from_file(path: str) -> str:
    """Read and return plain text content from a resume file."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def _parse_json_response(text: str) -> dict:
    """Extract JSON from LLM response, handling markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        # Strip markdown code fences
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        debug(f"JSON parse failed, raw: {text[:200]}")
        return {}


def resume_parser(state: Dict[str, Any]) -> Dict[str, Any]:
    """Parse resume text using LLM for structured extraction.

    Returns state update with resume_info, resume_debiased, confidence, missing_fields.
    """
    resume_text = (state.get("resume_text") or "").strip()
    # Normalize Unicode to ensure consistent LLM input across environments
    resume_text = unicodedata.normalize("NFKC", resume_text)

    # Input validation
    valid, error_msg = validate_resume_text(resume_text)
    if not valid:
        return {
            "messages": [{"role": "assistant", "content": f"[Resume Parser] {error_msg}"}],
            "resume_info": {},
            "parsing_confidence": 0.0,
            "errors": list(state.get("errors") or []) + [{"stage": "parsing", "error": error_msg}],
        }

    # Filter PII from raw text before LLM sees it
    debug("Resume Parser: filtering PII from resume text")
    filtered_resume_text, detected_pii = filter_pii(resume_text, use_ner=True)
    debug(f"Resume Parser: detected and filtered {len(detected_pii)} PII entities")

    from agents.orchestrator import get_autonomy
    llm = get_llm(model=get_model_for_task("resume_parsing"), temperature=0, task_type="resume_parsing")

    # Step 1: Extract structured resume info
    debug("Resume Parser: extracting structured info via LLM")
    if not get_autonomy().record_llm_call():
        raise RuntimeError("LLM call limit exceeded")
    extraction_response = logged_invoke(llm, [
        SystemMessage(content=RESUME_PARSER_SYSTEM),
        HumanMessage(content=spotlight_wrap(filtered_resume_text)),
    ], "resume_extraction")

    # Scan LLM output for PII leakage
    is_safe, leaked_pii = scan_output_for_pii(extraction_response.content)
    if not is_safe:
        debug(f"Resume Parser: PII leakage detected in LLM output ({len(leaked_pii)} entities)")

    resume_info = _parse_json_response(extraction_response.content)

    if not resume_info:
        # Fallback to basic regex extraction
        debug("Resume Parser: LLM extraction failed, using regex fallback")
        resume_info = _fallback_regex_parse(resume_text)

    # Step 2: Assess confidence
    debug("Resume Parser: assessing confidence")
    if not get_autonomy().record_llm_call():
        raise RuntimeError("LLM call limit exceeded")
    confidence_response = logged_invoke(llm, [
        SystemMessage(content=RESUME_PARSER_CONFIDENCE),
        HumanMessage(content=json.dumps(resume_info, indent=2)),
    ], "resume_confidence")
    confidence_data = _parse_json_response(confidence_response.content)
    confidence = confidence_data.get("confidence", 0.5)
    missing_fields = confidence_data.get("missing_fields", [])

    # Step 3: De-bias for downstream
    resume_debiased = strip_pii(resume_info)

    # Build display message
    contact = resume_info.get("contact_info", {})
    name = contact.get("name", "Unknown") if isinstance(contact, dict) else "Unknown"
    skills = resume_info.get("skills", {})
    tech_skills = skills.get("technical", []) if isinstance(skills, dict) else []
    yoe = resume_info.get("years_of_experience")
    msg = (
        f"[Resume Parser] Parsed resume for {name}. "
        f"Skills: {', '.join(tech_skills[:8]) or '—'}. "
        f"Experience: {yoe or '—'} yrs. "
        f"Confidence: {confidence:.0%}."
    )

    # HITL: flag for review if low confidence
    requires_review = confidence < 0.7

    result: Dict[str, Any] = {
        "messages": [{"role": "assistant", "content": msg}],
        "resume_info": resume_info,
        "resume_debiased": resume_debiased,
        "parsing_confidence": confidence,
        "missing_fields": missing_fields,
    }
    if requires_review:
        result["requires_human_approval"] = True

    valid, issues = validate_resume_output(result)
    if not valid:
        from datetime import datetime, timezone
        _guard_logger.warning(json.dumps({
            "event": "guardrail_triggered",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "guardrail": "output_validation",
            "agent": "resume_parser",
            "issues": issues,
        }))

    # --- XAI: Explainability trace ---
    xai_warnings = []
    if confidence < 0.7:
        xai_warnings.append(f"Low parsing confidence ({confidence:.0%})")
    if missing_fields:
        xai_warnings.append(f"Missing fields: {', '.join(missing_fields[:5])}")
    attributions = {
        "contact_info": 1.0 if resume_info.get("contact_info", {}).get("name") else 0.0,
        "skills": 1.0 if tech_skills else 0.0,
        "experience": 1.0 if resume_info.get("experience") else 0.0,
        "education": 1.0 if resume_info.get("education") else 0.0,
    }
    extraction_source = "llm" if resume_info and not (len(resume_info.get("skills", {}).get("technical", [])) == 0 and resume_info.get("years_of_experience") is None) else "regex_fallback"
    result["explainability_trace"] = create_trace(
        agent_name="resume_parser",
        prompt_version=RESUME_PARSER_PROMPT_VERSION,
        confidence=confidence,
        reasoning=f"Extracted via {extraction_source}; {len(tech_skills)} skills, {yoe or 0} yrs experience",
        feature_attributions=attributions,
        sources_consulted=[extraction_source],
        warnings=xai_warnings,
    ).to_dict()

    return result


def _fallback_regex_parse(text: str) -> dict:
    """Basic regex extraction as fallback when LLM fails."""
    import re

    info: Dict[str, Any] = {
        "contact_info": {"name": None, "email": None, "phone": None, "location": None},
        "professional_summary": None,
        "skills": {"technical": [], "soft": [], "certifications": []},
        "experience": [],
        "education": [],
        "industry_terms": [],
        "years_of_experience": None,
    }

    # Name
    m = re.search(r"(?:Name|Candidate)[:\-]\s*([A-Za-z .'-]{2,})", text, re.I)
    if m:
        info["contact_info"]["name"] = m.group(1).strip()

    # Years of experience
    m = re.search(r"(\d+)\s*\+?\s*(?:years|yrs)", text, re.I)
    if m:
        info["years_of_experience"] = int(m.group(1))

    # Skills from common tech list
    known_skills = [
        "python", "java", "javascript", "typescript", "c++", "spring", "spring boot",
        "angular", "react", "sql", "postgres", "postgresql", "mysql", "db2", "docker",
        "kubernetes", "aws", "gcp", "azure", "git", "maven", "jest", "junit",
        "redis", "microservices", "kafka", "go", "golang", "rust", "node",
        "nodejs", "vue", "svelte", "terraform", "ci/cd", "graphql", "rest",
    ]
    lower = text.lower()
    found = sorted({s for s in known_skills if s in lower})
    info["skills"]["technical"] = found

    return info

"""Output validation and grounding checks."""

from typing import Dict, Any, Tuple, List


def validate_resume_output(result: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate resume parser output has required structure."""
    issues = []
    info = result.get("resume_info", {})
    if not info:
        issues.append("resume_info is empty")
    if not isinstance(info, dict):
        issues.append("resume_info is not a dict")
    return (len(issues) == 0, issues)


def validate_job_discovery_output(result: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate job discovery output."""
    issues = []
    scored = result.get("scored_jobs", [])
    if not isinstance(scored, list):
        issues.append("scored_jobs is not a list")
    for i, job in enumerate(scored[:5]):
        if not isinstance(job, dict):
            issues.append(f"scored_jobs[{i}] is not a dict")
            continue
        if "score" not in job:
            issues.append(f"scored_jobs[{i}] missing 'score'")
        if "title" not in job:
            issues.append(f"scored_jobs[{i}] missing 'title'")
    return (len(issues) == 0, issues)


def validate_pitch_output(result: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate pitch generator output."""
    issues = []
    pitch = result.get("final_pitch", "")
    if not pitch:
        issues.append("final_pitch is empty")
    if isinstance(pitch, str) and len(pitch) < 50:
        issues.append("final_pitch is suspiciously short")
    return (len(issues) == 0, issues)


def check_grounding(summary: str, state: Dict[str, Any]) -> float:
    """Simple grounding check — verify summary references state data.

    Returns a grounding score 0.0–1.0 based on how many state fields are referenced.
    """
    if not summary:
        return 0.0

    summary_lower = summary.lower()
    checks = 0
    found = 0

    # Check if resume info is referenced
    info = state.get("resume_info", {})
    contact = info.get("contact_info", {}) if isinstance(info, dict) else {}
    name = contact.get("name") if isinstance(contact, dict) else None
    if name:
        checks += 1
        if name.lower() in summary_lower:
            found += 1

    # Check if top job is referenced
    scored = state.get("scored_jobs", [])
    if scored and isinstance(scored[0], dict):
        top_company = scored[0].get("company", "")
        if top_company:
            checks += 1
            if top_company.lower() in summary_lower:
                found += 1

    # Check if skill gaps are referenced
    gaps = state.get("skill_gaps", [])
    if gaps:
        checks += 1
        if any(
            g.get("skill", "").lower() in summary_lower
            for g in gaps[:3] if isinstance(g, dict)
        ):
            found += 1

    if checks == 0:
        return 1.0  # Nothing to check
    return found / checks

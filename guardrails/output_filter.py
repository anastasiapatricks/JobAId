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


def validate_market_intel_output(result: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate market intelligence output has required structure and data quality."""
    issues = []

    # skill_gaps validation
    skill_gaps = result.get("skill_gaps", [])
    if not isinstance(skill_gaps, list):
        issues.append("skill_gaps is not a list")
    else:
        for i, gap in enumerate(skill_gaps[:10]):
            if not isinstance(gap, dict):
                issues.append(f"skill_gaps[{i}] is not a dict")
                continue
            if not gap.get("skill"):
                issues.append(f"skill_gaps[{i}] missing 'skill'")
            if gap.get("importance") and gap["importance"] not in ("high", "medium", "low"):
                issues.append(f"skill_gaps[{i}] invalid importance: {gap['importance']}")
            if gap.get("category") and gap["category"] not in ("technical", "soft", "certification"):
                issues.append(f"skill_gaps[{i}] invalid category: {gap['category']}")

    # upskilling_roadmap validation
    roadmap = result.get("upskilling_roadmap", [])
    if not isinstance(roadmap, list):
        issues.append("upskilling_roadmap is not a list")
    else:
        for i, item in enumerate(roadmap[:10]):
            if not isinstance(item, dict):
                issues.append(f"upskilling_roadmap[{i}] is not a dict")
                continue
            if not item.get("skill"):
                issues.append(f"upskilling_roadmap[{i}] missing 'skill'")
            if "priority" in item and not isinstance(item["priority"], (int, float)):
                issues.append(f"upskilling_roadmap[{i}] priority is not a number")

    # salary_insights validation
    salary = result.get("salary_insights", {})
    if salary and not isinstance(salary, dict):
        issues.append("salary_insights is not a dict")
    elif isinstance(salary, dict) and salary:
        for field in ("min_salary", "max_salary", "median_salary"):
            val = salary.get(field)
            if val is not None and not isinstance(val, (int, float)):
                issues.append(f"salary_insights.{field} is not a number")
        if salary.get("min_salary") and salary.get("max_salary"):
            if salary["min_salary"] > salary["max_salary"]:
                issues.append("salary_insights.min_salary > max_salary")

    # industry_trends validation
    trends = result.get("industry_trends", [])
    if not isinstance(trends, list):
        issues.append("industry_trends is not a list")

    # market_outlook validation
    outlook = result.get("market_outlook", "")
    if outlook and not isinstance(outlook, str):
        issues.append("market_outlook is not a string")

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

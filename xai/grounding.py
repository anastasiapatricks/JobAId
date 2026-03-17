"""Pitch grounding verification — checks cover letter claims against resume and job data."""

import re
from typing import Any, Dict, List


def verify_pitch_grounding(
    pitch_text: str,
    resume_info: Dict[str, Any],
    job_info: Dict[str, Any],
) -> Dict[str, Any]:
    """Verify that claims in a cover letter are grounded in resume and job data.

    Checks:
    - Skills mentioned in the pitch appear in the resume
    - Company name matches the job listing
    - Experience claims can be traced to resume entries

    Returns grounding_score (0-1), verified/unverified claims, and warnings.
    """
    if not pitch_text:
        return {
            "grounding_score": 0.0,
            "verified_claims": [],
            "unverified_claims": [],
            "warnings": ["Empty pitch text"],
        }

    pitch_lower = pitch_text.lower()
    verified = []
    unverified = []
    warnings = []

    # --- Check skills mentioned in pitch ---
    skills = resume_info.get("skills", {})
    if isinstance(skills, dict):
        all_skills = (
            skills.get("technical", [])
            + skills.get("soft", [])
            + skills.get("certifications", [])
        )
    elif isinstance(skills, list):
        all_skills = skills
    else:
        all_skills = []

    for skill in all_skills:
        if skill.lower() in pitch_lower:
            verified.append(f"Skill '{skill}' found in resume")

    # --- Check company name ---
    company = job_info.get("company", "")
    if company and company.lower() in pitch_lower:
        verified.append(f"Company '{company}' correctly referenced")
    elif company:
        unverified.append(f"Company '{company}' not mentioned in pitch")
        warnings.append("Cover letter does not mention the target company by name")

    # --- Check job title ---
    job_title = job_info.get("title", "")
    if job_title and job_title.lower() in pitch_lower:
        verified.append(f"Job title '{job_title}' correctly referenced")

    # --- Check experience claims ---
    experience = resume_info.get("experience", [])
    for exp in experience:
        if not isinstance(exp, dict):
            continue
        exp_company = exp.get("company", "")
        exp_title = exp.get("title", "")
        if exp_company and exp_company.lower() in pitch_lower:
            verified.append(f"Experience at '{exp_company}' is grounded")
        if exp_title and exp_title.lower() in pitch_lower:
            verified.append(f"Role '{exp_title}' is grounded")

    # --- Check for potentially ungrounded claims ---
    # Look for years of experience claims
    years_claimed = re.findall(r"(\d+)\+?\s*years?\s*(?:of\s+)?experience", pitch_lower)
    actual_years = resume_info.get("years_of_experience")
    for claimed in years_claimed:
        claimed_int = int(claimed)
        if actual_years is not None and abs(claimed_int - actual_years) <= 1:
            verified.append(f"{claimed_int} years experience matches resume ({actual_years})")
        elif actual_years is not None:
            unverified.append(
                f"Claims {claimed_int} years but resume shows {actual_years}"
            )
            warnings.append(f"Experience years mismatch: claimed {claimed_int}, actual {actual_years}")

    # --- Compute grounding score ---
    total = len(verified) + len(unverified)
    grounding_score = len(verified) / max(total, 1)

    return {
        "grounding_score": round(grounding_score, 4),
        "verified_claims": verified,
        "unverified_claims": unverified,
        "warnings": warnings,
    }

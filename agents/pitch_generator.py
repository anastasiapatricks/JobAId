# agents/pitch_generator.py

from typing import Dict, Any
from tools.wikipedia import get_company_summary
from utils import debug

def pitch_generator(state: Dict[str, Any]) -> Dict[str, Any]:

    """
    Generate a cover letter using LLM when prompted by user.

    Args:
        state: Resume info parsed from user, job relevance, best job ranked.

    Returns:
        Formatted cover letter string
    """
    debug("Tool Pitch Generator has been called.")


    info = state.get("resume_info") or {}
    top = (state.get("scored_jobs") or [{}])
    best = top[0].get("job") if top else None

    name = info.get("name") or "Candidate"
    skills = ", ".join(info.get("skills") or []) or "relevant experience"
    jobline = f"{best['title']} at {best['company']}" if best and best.get('title') and best.get('company') else "the role"

    company = best["company"] if best and "company" in best else None
    debug(f"Initial company from scored_jobs: {company}")

    # Fallback: Try to get company from top job in job_listings if not found
    if not company or str(company).strip().lower() in ("none", "", "null"):
        job_listings = state.get("job_listings") or []
        if job_listings and isinstance(job_listings, list):
            alt_company = job_listings[0].get("company") if job_listings[0] else None
            debug(f"Fallback: company from top job_listings: {alt_company}")
            if alt_company and str(alt_company).strip().lower() not in ("none", "", "null"):
                company = alt_company
        else:
            debug("No job_listings available for fallback company.")

    debug(f"Final company to use: {company}")

    # Handle missing or empty company name
    if not company or str(company).strip().lower() in ("none", "", "null"):
        debug("No valid company name found; skipping Wikipedia lookup and using fallback pitch.")
        pitch = (
            f"Hi Hiring Team, I'm {name}. I’ve worked extensively with {skills} and I’m excited about {jobline}. "
            f"I believe my background aligns well with your needs. "
            f"I'd love to discuss how I can contribute. Thanks for your consideration."
        )
        messages = [
            {"role": "assistant", "content": "Generated a fallback pitch (no company info available)."},
            {"role": "assistant", "content": f"=== PITCH ===\n{pitch}"},
        ]
    else:
        debug(f"Fetching Wikipedia info for company: {company}")
        company_info = get_company_summary(company)
        pitch = (
            f"Hi Hiring Team, I'm {name}. I’ve worked extensively with {skills} and I’m excited about {jobline}. "
            f"I believe my background aligns well with your needs. "
            f"Here's what excites me about {company}: {company_info}\n"
            f"I'd love to discuss how I can contribute. Thanks for your consideration."
        )
        messages = [
            {"role": "assistant", "content": "Generated a tailored pitch using Wikipedia company info. Used [TOOL] Wikipedia to fetch company summary."},
            {"role": "assistant", "content": f"=== PITCH ===\n{pitch}"},
        ]

    return {
        "messages": messages,
        "final_pitch": pitch,
    }

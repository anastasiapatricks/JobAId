"""Pitch Generator — 4-step prompt chaining for cover letter generation."""

from typing import Dict, Any
import json

from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

from config.settings import settings
from config.prompts import (
    PITCH_RESEARCH_SYSTEM,
    PITCH_MATCH_ANALYSIS_SYSTEM,
    PITCH_DRAFT_SYSTEM,
    PITCH_REVIEW_SYSTEM,
)
from tools.wikipedia import get_company_summary
from utils import debug


def _parse_json_response(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def _get_best_job(state: Dict[str, Any]) -> Dict[str, Any]:
    """Get the top-scored job from state."""
    scored = state.get("scored_jobs") or []
    if scored:
        return scored[0]
    listings = state.get("job_listings") or []
    if listings:
        return listings[0]
    return {}


def _build_candidate_summary(state: Dict[str, Any]) -> str:
    """Build a text summary of the candidate."""
    info = state.get("resume_info") or {}
    parts = []

    contact = info.get("contact_info", {})
    name = contact.get("name") if isinstance(contact, dict) else None
    if name:
        parts.append(f"Name: {name}")

    skills = info.get("skills", {})
    if isinstance(skills, dict):
        tech = skills.get("technical", [])
        if tech:
            parts.append(f"Technical skills: {', '.join(tech)}")
    elif isinstance(skills, list) and skills:
        parts.append(f"Skills: {', '.join(skills)}")

    yoe = info.get("years_of_experience")
    if yoe:
        parts.append(f"Years of experience: {yoe}")

    summary = info.get("professional_summary")
    if summary:
        parts.append(f"Professional summary: {summary}")

    experience = info.get("experience", [])
    if experience:
        for exp in experience[:3]:
            title = exp.get("title", "")
            company = exp.get("company", "")
            if title:
                parts.append(f"Previous role: {title}" + (f" at {company}" if company else ""))

    return "\n".join(parts) if parts else "Candidate information not available."


def pitch_generator(state: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a cover letter through 4-step prompt chaining.

    1. Company research (Wikipedia + job details)
    2. Match analysis (candidate-job fit)
    3. Draft generation
    4. Quality review
    """
    best_job = _get_best_job(state)
    if not best_job:
        return {
            "messages": [{"role": "assistant", "content": "[Pitch Generator] No job available to generate pitch for."}],
            "final_pitch": "",
        }

    company = best_job.get("company", "")
    job_title = best_job.get("title", "the role")
    candidate_summary = _build_candidate_summary(state)
    llm = ChatOpenAI(model=settings.default_model, temperature=0.7)

    draft_pitches = []

    # ─── Step 1: Company Research ───
    debug("Pitch Generator: Step 1 — company research")
    company_info = ""
    if company:
        company_info = get_company_summary(company)

    job_context = (
        f"Company: {company}\n"
        f"Job title: {job_title}\n"
        f"Location: {best_job.get('location', 'N/A')}\n"
        f"Job keywords: {', '.join(best_job.get('keywords', []))}\n"
        f"Job description: {best_job.get('description', 'N/A')[:500]}\n"
    )

    research_response = llm.invoke([
        SystemMessage(content=PITCH_RESEARCH_SYSTEM),
        HumanMessage(content=f"{job_context}\n\nWikipedia info:\n{company_info}"),
    ])
    company_research = research_response.content

    # ─── Step 2: Match Analysis ───
    debug("Pitch Generator: Step 2 — match analysis")
    match_prompt = (
        f"Candidate:\n{candidate_summary}\n\n"
        f"Job:\n{job_context}\n\n"
        f"Company research:\n{company_research}"
    )
    match_response = llm.invoke([
        SystemMessage(content=PITCH_MATCH_ANALYSIS_SYSTEM),
        HumanMessage(content=match_prompt),
    ])
    match_analysis = _parse_json_response(match_response.content)
    if not match_analysis:
        match_analysis = {"strengths": [], "gaps": [], "value_propositions": [], "talking_points": []}

    # ─── Step 3: Draft Generation ───
    debug("Pitch Generator: Step 3 — draft generation")
    draft_prompt = (
        f"Write a cover letter for this candidate applying to {job_title} at {company}.\n\n"
        f"Candidate:\n{candidate_summary}\n\n"
        f"Company research:\n{company_research}\n\n"
        f"Match analysis:\n{json.dumps(match_analysis, indent=2)}\n\n"
        f"Write a compelling, personalized cover letter."
    )
    draft_response = llm.invoke([
        SystemMessage(content=PITCH_DRAFT_SYSTEM),
        HumanMessage(content=draft_prompt),
    ])
    draft = draft_response.content
    draft_pitches.append({"version": "draft", "content": draft})

    # ─── Step 4: Quality Review ───
    debug("Pitch Generator: Step 4 — quality review")
    review_response = llm.invoke([
        SystemMessage(content=PITCH_REVIEW_SYSTEM),
        HumanMessage(content=f"Review and improve this cover letter:\n\n{draft}"),
    ])
    final_pitch = review_response.content
    draft_pitches.append({"version": "final", "content": final_pitch})

    msg = f"[Pitch Generator] Generated cover letter for {job_title} at {company} (4-step chain: research → analysis → draft → review)."

    return {
        "messages": [
            {"role": "assistant", "content": msg},
            {"role": "assistant", "content": f"=== COVER LETTER ===\n{final_pitch}"},
        ],
        "draft_pitches": draft_pitches,
        "final_pitch": final_pitch,
    }

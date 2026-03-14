"""Pitch Generator — 4-step prompt chaining for cover letter generation."""

from typing import Dict, Any
import json

from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

import logging

from config.settings import settings
from config.prompts import (
    PITCH_RESEARCH_SYSTEM,
    PITCH_MATCH_ANALYSIS_SYSTEM,
    PITCH_DRAFT_SYSTEM,
    PITCH_REVIEW_SYSTEM,
)
from guardrails.output_filter import validate_pitch_output
from guardrails.model_router import get_model_for_task
from tools.tavily_search import search_company
from tools.wikipedia import get_company_summary
from utils import debug, get_latest_results
from utils.llm_logger import logged_invoke

_guard_logger = logging.getLogger("jobaid.guardrails")


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
    latest = get_latest_results(state)
    scored = state.get("scored_jobs") or latest.get("scored_jobs") or []
    if scored:
        return scored[0]
    listings = latest.get("job_listings") or state.get("job_listings") or []
    if listings:
        return listings[0]
    return {}


def _build_candidate_summary(state: Dict[str, Any]) -> str:
    """Build a text summary of the candidate."""
    latest = get_latest_results(state)
    info = latest.get("resume_info") or state.get("resume_info") or {}
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
    from agents.orchestrator import get_autonomy
    candidate_summary = _build_candidate_summary(state)
    llm = ChatOpenAI(model=get_model_for_task("pitch_draft"), temperature=0.7)

    draft_pitches = []

    # ─── Step 1: Company Research ───
    debug("Pitch Generator: Step 1 — company research")
    company_info = ""
    if company:
        company_info = search_company(company)
        if not company_info:
            debug("Pitch Generator: Tavily company search empty, falling back to Wikipedia")
            company_info = get_company_summary(company)

    job_context = (
        f"Company: {company}\n"
        f"Job title: {job_title}\n"
        f"Location: {best_job.get('location', 'N/A')}\n"
        f"Job keywords: {', '.join(best_job.get('keywords', []))}\n"
        f"Job description: {best_job.get('description', 'N/A')[:500]}\n"
    )

    if not get_autonomy().record_llm_call():
        raise RuntimeError("LLM call limit exceeded")
    research_response = logged_invoke(llm, [
        SystemMessage(content=PITCH_RESEARCH_SYSTEM),
        HumanMessage(content=f"{job_context}\n\nCompany info:\n{company_info}"),
    ], "pitch_research")
    company_research = research_response.content

    # ─── Step 2: Match Analysis ───
    debug("Pitch Generator: Step 2 — match analysis")
    match_prompt = (
        f"Candidate:\n{candidate_summary}\n\n"
        f"Job:\n{job_context}\n\n"
        f"Company research:\n{company_research}"
    )
    if not get_autonomy().record_llm_call():
        raise RuntimeError("LLM call limit exceeded")
    match_response = logged_invoke(llm, [
        SystemMessage(content=PITCH_MATCH_ANALYSIS_SYSTEM),
        HumanMessage(content=match_prompt),
    ], "pitch_match_analysis")
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
    if not get_autonomy().record_llm_call():
        raise RuntimeError("LLM call limit exceeded")
    draft_response = logged_invoke(llm, [
        SystemMessage(content=PITCH_DRAFT_SYSTEM),
        HumanMessage(content=draft_prompt),
    ], "pitch_draft")
    draft = draft_response.content
    draft_pitches.append({"version": "draft", "content": draft})

    # ─── Step 4: Quality Review ───
    debug("Pitch Generator: Step 4 — quality review")
    if not get_autonomy().record_llm_call():
        raise RuntimeError("LLM call limit exceeded")
    review_llm = ChatOpenAI(model=get_model_for_task("pitch_review"), temperature=0.7)
    review_response = logged_invoke(review_llm, [
        SystemMessage(content=PITCH_REVIEW_SYSTEM),
        HumanMessage(content=f"Review and improve this cover letter:\n\n{draft}"),
    ], "pitch_review")
    final_pitch = review_response.content
    draft_pitches.append({"version": "final", "content": final_pitch})

    msg = f"[Pitch Generator] Generated cover letter for {job_title} at {company} (4-step chain: research → analysis → draft → review)."

    result = {
        "messages": [
            {"role": "assistant", "content": msg},
            {"role": "assistant", "content": f"=== COVER LETTER ===\n{final_pitch}"},
        ],
        "draft_pitches": draft_pitches,
        "final_pitch": final_pitch,
    }

    valid, issues = validate_pitch_output(result)
    if not valid:
        from datetime import datetime, timezone
        _guard_logger.warning(json.dumps({
            "event": "guardrail_triggered",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "guardrail": "output_validation",
            "agent": "pitch_generator",
            "issues": issues,
        }))

    return result

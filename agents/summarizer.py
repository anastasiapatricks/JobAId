"""Grounded summarizer with explainability — uses structured state data only."""

import json
from typing import Dict, Any

from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

from config.settings import settings
from config.prompts import SUMMARIZER_SYSTEM
from utils import debug


def _build_grounded_context(state: Dict[str, Any]) -> str:
    """Build a context string from structured state data only (no raw messages)."""
    sections = []

    # Resume info
    info = state.get("resume_info") or {}
    if info:
        contact = info.get("contact_info", {})
        name = contact.get("name", "Unknown") if isinstance(contact, dict) else "Unknown"
        skills = info.get("skills", {})
        tech = skills.get("technical", []) if isinstance(skills, dict) else []
        yoe = info.get("years_of_experience")
        sections.append(
            f"RESUME:\n"
            f"  Candidate: {name}\n"
            f"  Technical skills: {', '.join(tech) if tech else 'N/A'}\n"
            f"  Years of experience: {yoe or 'N/A'}\n"
            f"  Parsing confidence: {state.get('parsing_confidence', 'N/A')}"
        )

    # Job matches
    scored = state.get("scored_jobs") or []
    if scored:
        job_lines = []
        for i, j in enumerate(scored[:5], 1):
            job_lines.append(
                f"  {i}. {j.get('title', '?')} @ {j.get('company', '?')} "
                f"— Score: {j.get('score', '?')}/100 — {j.get('explanation', '')}"
            )
        sections.append("JOB MATCHES:\n" + "\n".join(job_lines))

    # Skill gaps
    gaps = state.get("skill_gaps") or []
    if gaps:
        gap_lines = [f"  - {g.get('skill', '?')} ({g.get('importance', 'medium')})" for g in gaps[:8]]
        sections.append("SKILL GAPS:\n" + "\n".join(gap_lines))

    # Upskilling roadmap
    roadmap = state.get("upskilling_roadmap") or []
    if roadmap:
        road_lines = []
        for item in roadmap[:5]:
            courses = item.get("recommended_courses", [])
            road_lines.append(
                f"  - {item.get('skill', '?')}: {', '.join(courses[:2]) if courses else 'self-study'}"
            )
        sections.append("UPSKILLING ROADMAP:\n" + "\n".join(road_lines))

    # Salary insights
    salary = state.get("salary_insights")
    if salary and isinstance(salary, dict):
        currency = salary.get("currency", "SGD")
        mn = salary.get("min_salary")
        mx = salary.get("max_salary")
        if mn and mx:
            sections.append(f"SALARY INSIGHTS:\n  Range: {currency} {mn:,.0f} – {mx:,.0f}")

    # Industry trends
    trends = state.get("industry_trends") or []
    if trends:
        trend_lines = [f"  - {t}" for t in trends[:4]]
        sections.append("INDUSTRY TRENDS:\n" + "\n".join(trend_lines))

    # Cover letter
    pitch = state.get("final_pitch")
    if pitch:
        sections.append(f"COVER LETTER:\n  (Generated for top match — {len(pitch)} chars)")

    # Errors / fallbacks
    errors = state.get("errors") or []
    fallbacks = state.get("fallback_used") or []
    if errors or fallbacks:
        sections.append(
            f"NOTES:\n"
            f"  Errors: {len(errors)}\n"
            f"  Fallbacks used: {', '.join(fallbacks) if fallbacks else 'None'}"
        )

    return "\n\n".join(sections) if sections else "No data available to summarize."


def summarizer(state: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a grounded summary using only structured state data."""
    context = _build_grounded_context(state)

    try:
        llm = ChatOpenAI(model=settings.default_model, temperature=0)
        response = llm.invoke([
            SystemMessage(content=SUMMARIZER_SYSTEM),
            HumanMessage(content=f"Session data:\n\n{context}\n\nGenerate the final report."),
        ])
        summary_text = response.content.strip()
    except Exception as exc:
        debug(f"Summarizer LLM error: {exc}")
        summary_text = f"=== JobAId Summary ===\n\n{context}"

    # Build decision log summary
    log = state.get("decision_log") or []
    log_text = ""
    if log:
        log_text = "\n\n--- Decision Log ---\n" + "\n".join(
            f"[{e.get('stage')}] {e.get('action')}: {e.get('reasoning')}" for e in log
        )

    full_summary = summary_text + log_text

    return {
        "messages": [{"role": "assistant", "content": f"[Summarizer] Final report generated."}],
        "summary": full_summary,
    }

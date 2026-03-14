"""Market Intelligence agent — skill gaps, upskilling, salary, trends via RAG."""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

from config.settings import settings
from config.prompts import MARKET_INTELLIGENCE_SYSTEM, MARKET_INTELLIGENCE_PROMPT_VERSION
from guardrails.input_filter import validate_job_query
from guardrails.output_filter import validate_market_intel_output
from guardrails.model_router import get_model_for_task
from tools.chromadb_tools import search_collection
from tools.tavily_search import search_courses, search_trends, search_salary
from utils import debug, get_latest_results
from utils.llm_logger import logged_invoke

_agent_logger = logging.getLogger("jobaid.market_intel")


def _parse_json_response(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        debug(f"Market Intel JSON parse failed: {text[:200]}")
        return {}


def _get_candidate_skills(state: Dict[str, Any]) -> List[str]:
    """Extract flat skill list from resume info."""
    latest = get_latest_results(state)
    info = latest.get("resume_debiased") or state.get("resume_debiased") or latest.get("resume_info") or state.get("resume_info") or {}
    skills = info.get("skills", {})
    if isinstance(skills, dict):
        return skills.get("technical", []) + skills.get("soft", []) + skills.get("certifications", [])
    if isinstance(skills, list):
        return skills
    return []


def _get_top_job_requirements(state: Dict[str, Any]) -> List[str]:
    """Collect required skills from top scored jobs."""
    latest = get_latest_results(state)
    scored = latest.get("scored_jobs") or state.get("scored_jobs") or []
    all_kws: List[str] = []
    for job in scored[:5]:
        all_kws.extend(job.get("keywords", []))
    return list(set(all_kws))


def _lookup_salary(job_query: str, years_exp: int | None) -> Dict[str, Any]:
    """Look up salary data from seed data (structured, not vector search)."""
    try:
        from vectordb.seed_data import load_salary_data
        salary_data = load_salary_data()
    except Exception:
        return {}

    if not salary_data:
        return {}

    # Determine experience level
    if years_exp is not None:
        if years_exp <= 2:
            level = "junior"
        elif years_exp <= 6:
            level = "mid"
        else:
            level = "senior"
    else:
        level = "mid"

    query_lower = job_query.lower()

    # Find best matching salary entry
    best = None
    best_score = 0
    for entry in salary_data:
        role_lower = entry.get("role", "").lower()
        entry_level = entry.get("level", "")
        score = 0
        # Role match
        for term in query_lower.split():
            if term in role_lower:
                score += 2
        # Level match
        if entry_level == level:
            score += 1
        if score > best_score:
            best_score = score
            best = entry

    if best:
        return {
            "min_salary": best.get("min_salary"),
            "max_salary": best.get("max_salary"),
            "median_salary": best.get("median_salary"),
            "currency": best.get("currency", "SGD"),
            "experience_level": best.get("level", level),
            "source": "seed_data",
        }
    return {}


def _build_skill_gap_explanations(
    candidate_skills: List[str], job_requirements: List[str], skill_gaps: List[dict], scored_jobs: List[dict]
) -> List[dict]:
    """Add explainability trace to each skill gap — which jobs demand it and why it matters.

    This provides local explanations for the XAI requirement, showing users
    exactly which job listings drove each skill gap identification.
    """
    candidate_lower = {s.lower() for s in candidate_skills}
    for gap in skill_gaps:
        skill_name = gap.get("skill", "")
        skill_lower = skill_name.lower()
        # Find which jobs require this skill
        demanding_jobs = []
        for job in scored_jobs[:10]:
            job_keywords = [kw.lower() for kw in job.get("keywords", [])]
            job_desc = (job.get("description", "") + " " + job.get("title", "")).lower()
            if skill_lower in job_keywords or skill_lower in job_desc:
                demanding_jobs.append(job.get("title", "Unknown"))
        gap["demanded_by_jobs"] = demanding_jobs[:5]
        gap["in_candidate_profile"] = skill_lower in candidate_lower
        gap["explanation"] = (
            f"'{skill_name}' is required by {len(demanding_jobs)} of your top job matches"
            f" ({', '.join(demanding_jobs[:3]) or 'general market demand'})"
            f" but {'is' if gap['in_candidate_profile'] else 'is not'} in your current profile."
        )
    return skill_gaps


def _verify_sources(
    upskilling_roadmap: List[dict], courses_context: str, trends_context: str
) -> List[dict]:
    """Hallucination guard — cross-check recommended courses against source data.

    Flags courses that cannot be traced back to Tavily search results or ChromaDB
    RAG context, helping users distinguish grounded vs LLM-generated recommendations.
    """
    source_text_lower = (courses_context + " " + trends_context).lower()
    for item in upskilling_roadmap:
        verified_courses = []
        for course in item.get("recommended_courses", []):
            course_str = str(course)
            # Check if the course name or URL appears in source context
            course_lower = course_str.lower()
            # Extract meaningful tokens (skip very short words)
            tokens = [t for t in course_lower.split() if len(t) > 3]
            match_count = sum(1 for t in tokens if t in source_text_lower)
            is_grounded = match_count >= min(2, len(tokens)) if tokens else False
            verified_courses.append({
                "course": course_str,
                "source_verified": is_grounded,
            })
        item["verified_courses"] = verified_courses
        item["grounding_score"] = (
            sum(1 for vc in verified_courses if vc["source_verified"])
            / max(len(verified_courses), 1)
        )
    return upskilling_roadmap


def skill_triage(state: Dict[str, Any]) -> Dict[str, Any]:
    """Quick skill-gap triage — pure Python, no LLM calls.

    Compares candidate skills against each scored job's keywords to produce
    a fast "skills you have vs skills you need" snapshot. Runs automatically
    after job discovery to give users an instant overview before they decide
    whether to request a full deep-dive market analysis.
    """
    candidate_skills = _get_candidate_skills(state)
    candidate_lower = {s.lower().strip() for s in candidate_skills if s}

    latest = get_latest_results(state)
    scored_jobs = latest.get("scored_jobs") or state.get("scored_jobs") or []

    triage_results = []
    for job in scored_jobs[:10]:
        job_keywords = job.get("keywords", [])
        keywords_lower = {kw.lower().strip() for kw in job_keywords if kw}

        matched = sorted(candidate_lower & keywords_lower)
        missing = sorted(keywords_lower - candidate_lower)
        total = len(keywords_lower)
        ratio = len(matched) / max(total, 1)

        triage_results.append({
            "title": job.get("title", "Unknown"),
            "company": job.get("company", "Unknown"),
            "score": job.get("score", 0),
            "skills_matched": matched,
            "skills_missing": missing,
            "match_ratio": round(ratio, 2),
        })

    # Build summary message
    if triage_results:
        top = triage_results[0]
        n_matched = len(top["skills_matched"])
        n_total = n_matched + len(top["skills_missing"])
        missing_text = ", ".join(top["skills_missing"][:4]) or "none"
        msg = (
            f"[Skill Triage] Quick scan of {len(triage_results)} jobs: "
            f"your top match is {top['title']} at {top['company']} "
            f"({n_matched}/{n_total} skills). "
            f"Key gaps: {missing_text}."
        )
    else:
        msg = "[Skill Triage] No scored jobs to analyze."

    return {
        "skill_triage": triage_results,
        "messages": [{"role": "assistant", "content": msg}],
    }


def market_intelligence(state: Dict[str, Any]) -> Dict[str, Any]:
    """Deep-dive market analysis: skill gaps, upskilling, salary, trends via RAG."""
    candidate_skills = _get_candidate_skills(state)
    job_requirements = _get_top_job_requirements(state)
    job_query = state.get("job_query", "")

    # Input validation
    valid, error_msg = validate_job_query(job_query)
    if not valid:
        return {
            "messages": [{"role": "assistant", "content": f"[Market Intelligence] {error_msg}"}],
            "skill_gaps": [],
            "upskilling_roadmap": [],
            "salary_insights": {},
            "industry_trends": [],
            "market_outlook": "",
        }

    latest = get_latest_results(state)
    resume_info = latest.get("resume_info") or state.get("resume_info") or {}
    years_exp = resume_info.get("years_of_experience")

    # --- Courses: Tavily first, RAG fallback ---
    courses_context = search_courses(job_requirements[:5], job_query)
    if not courses_context:
        debug("Market Intel: Tavily courses empty, falling back to RAG")
        try:
            from vectordb.collections import get_courses_collection
            courses_coll = get_courses_collection()
            skill_query = f"courses for {' '.join(job_requirements[:5])} skills development"
            course_results = search_collection(courses_coll, skill_query, n_results=5)
            if course_results:
                lines = []
                for r in course_results:
                    meta = r.get("metadata") or {}
                    parts = [r["document"]]
                    if meta.get("provider"):
                        parts.append(f"Provider: {meta['provider']}")
                    if meta.get("url"):
                        parts.append(f"URL: {meta['url']}")
                    if meta.get("level"):
                        parts.append(f"Level: {meta['level']}")
                    if meta.get("duration"):
                        parts.append(f"Duration: {meta['duration']}")
                    lines.append("- " + " | ".join(parts))
                courses_context = "Available courses:\n" + "\n".join(lines)
        except Exception as exc:
            debug(f"Market Intel: courses RAG error: {exc}")

    # --- Trends: Tavily first, RAG fallback ---
    trends_context = search_trends(job_query)
    if not trends_context:
        debug("Market Intel: Tavily trends empty, falling back to RAG")
        try:
            from vectordb.collections import get_trends_collection
            trends_coll = get_trends_collection()
            trend_results = search_collection(trends_coll, job_query, n_results=4)
            if trend_results:
                lines = []
                for r in trend_results:
                    meta = r.get("metadata") or {}
                    parts = [r["document"]]
                    if meta.get("industry"):
                        parts.append(f"Industry: {meta['industry']}")
                    if meta.get("year"):
                        parts.append(f"Year: {meta['year']}")
                    if meta.get("topic"):
                        parts.append(f"Topic: {meta['topic']}")
                    lines.append("- " + " | ".join(parts))
                trends_context = "Industry trends:\n" + "\n".join(lines)
        except Exception as exc:
            debug(f"Market Intel: trends RAG error: {exc}")

    # --- Salary: Tavily first, seed-data fallback ---
    salary_web_context = search_salary(job_query, years_exp)
    salary_insights = _lookup_salary(job_query, years_exp)

    # LLM analysis
    prompt_parts = [
        f"Candidate skills: {', '.join(candidate_skills)}",
        f"Years of experience: {years_exp or 'Unknown'}",
        f"Target job requirements (from top matches): {', '.join(job_requirements)}",
        f"Job query: {job_query}",
        "",
        courses_context or "",
        "",
        trends_context or "",
        "",
    ]
    if salary_web_context:
        prompt_parts.append(salary_web_context)
        prompt_parts.append("")
    prompt_parts.append(
        f"Salary data: {json.dumps(salary_insights) if salary_insights else 'Not available'}"
    )
    prompt_parts.append("")
    prompt_parts.append(
        "Analyze skill gaps, create upskilling roadmap, provide salary insights and industry trends."
    )
    user_prompt = "\n".join(prompt_parts)

    try:
        from agents.orchestrator import get_autonomy
        if not get_autonomy().record_llm_call():
            raise RuntimeError("LLM call limit exceeded")
        llm = ChatOpenAI(model=get_model_for_task("market_intelligence"), temperature=0)
        response = logged_invoke(llm, [
            SystemMessage(content=MARKET_INTELLIGENCE_SYSTEM),
            HumanMessage(content=user_prompt),
        ], "market_analysis")
        result = _parse_json_response(response.content)
    except Exception as exc:
        debug(f"Market Intel: LLM error: {exc}")
        result = {}

    skill_gaps = result.get("skill_gaps", [])
    if isinstance(skill_gaps, list):
        # Normalize to dicts
        skill_gaps = [
            g if isinstance(g, dict) else {"skill": str(g), "importance": "medium", "category": "technical"}
            for g in skill_gaps
        ]
    else:
        skill_gaps = []

    upskilling_roadmap = result.get("upskilling_roadmap", [])
    if isinstance(upskilling_roadmap, list):
        upskilling_roadmap = [
            u if isinstance(u, dict) else {"skill": str(u), "priority": 1, "recommended_courses": []}
            for u in upskilling_roadmap
        ]
    else:
        upskilling_roadmap = []

    # Merge LLM salary insights with seed data
    llm_salary = result.get("salary_insights", {})
    if isinstance(llm_salary, dict) and salary_insights:
        salary_insights.update({k: v for k, v in llm_salary.items() if v})
    elif isinstance(llm_salary, dict):
        salary_insights = llm_salary

    industry_trends = result.get("industry_trends", [])
    if not isinstance(industry_trends, list):
        industry_trends = [str(industry_trends)] if industry_trends else []

    market_outlook = result.get("market_outlook", "")
    if not isinstance(market_outlook, str):
        market_outlook = str(market_outlook) if market_outlook else ""

    # --- Output validation ---
    validation_result = {
        "skill_gaps": skill_gaps,
        "upskilling_roadmap": upskilling_roadmap,
        "salary_insights": salary_insights,
        "industry_trends": industry_trends,
        "market_outlook": market_outlook,
    }
    valid, issues = validate_market_intel_output(validation_result)
    if not valid:
        debug(f"Market Intel output validation issues: {issues}")
        _agent_logger.warning(json.dumps({
            "event": "output_validation_warning",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "issues": issues,
            "prompt_version": MARKET_INTELLIGENCE_PROMPT_VERSION,
        }))

    # --- Explainability: enrich skill gaps with reasoning trace ---
    scored_jobs = latest.get("scored_jobs") or state.get("scored_jobs") or []
    skill_gaps = _build_skill_gap_explanations(
        candidate_skills, job_requirements, skill_gaps, scored_jobs
    )

    # --- Hallucination guard: verify course recommendations against sources ---
    upskilling_roadmap = _verify_sources(
        upskilling_roadmap, courses_context or "", trends_context or ""
    )

    # Log prompt version for MLSecOps traceability
    _agent_logger.info(json.dumps({
        "event": "market_intel_complete",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prompt_version": MARKET_INTELLIGENCE_PROMPT_VERSION,
        "skill_gaps_count": len(skill_gaps),
        "upskilling_items": len(upskilling_roadmap),
        "grounded_courses": sum(
            1 for item in upskilling_roadmap
            for vc in item.get("verified_courses", [])
            if vc.get("source_verified")
        ),
        "total_courses": sum(
            len(item.get("verified_courses", []))
            for item in upskilling_roadmap
        ),
        "output_valid": valid,
    }))

    # Build message
    gaps_text = ", ".join(g.get("skill", "?") for g in skill_gaps[:5]) if skill_gaps else "None identified"
    msg = (
        f"[Market Intelligence] "
        f"Skill gaps: {gaps_text}. "
        f"Upskilling items: {len(upskilling_roadmap)}. "
        f"Trends: {len(industry_trends)}."
    )

    return {
        "messages": [{"role": "assistant", "content": msg}],
        "skill_gaps": skill_gaps,
        "upskilling_roadmap": upskilling_roadmap,
        "salary_insights": salary_insights,
        "industry_trends": industry_trends,
        "market_outlook": market_outlook,
    }

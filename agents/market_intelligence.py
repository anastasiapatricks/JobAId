"""Market Intelligence agent — skill gaps, upskilling, salary, trends via RAG."""

import json
from typing import Dict, Any, List

from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

from config.settings import settings
from config.prompts import MARKET_INTELLIGENCE_SYSTEM
from tools.chromadb_tools import search_collection
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
        debug(f"Market Intel JSON parse failed: {text[:200]}")
        return {}


def _get_candidate_skills(state: Dict[str, Any]) -> List[str]:
    """Extract flat skill list from resume info."""
    info = state.get("resume_debiased") or state.get("resume_info") or {}
    skills = info.get("skills", {})
    if isinstance(skills, dict):
        return skills.get("technical", []) + skills.get("soft", []) + skills.get("certifications", [])
    if isinstance(skills, list):
        return skills
    return []


def _get_top_job_requirements(state: Dict[str, Any]) -> List[str]:
    """Collect required skills from top scored jobs."""
    scored = state.get("scored_jobs") or []
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


def market_intelligence(state: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze market intelligence: skill gaps, upskilling, salary, trends."""
    candidate_skills = _get_candidate_skills(state)
    job_requirements = _get_top_job_requirements(state)
    job_query = state.get("job_query", "")
    resume_info = state.get("resume_info") or {}
    years_exp = resume_info.get("years_of_experience")

    # RAG: query courses collection for upskilling
    courses_context = ""
    try:
        from vectordb.collections import get_courses_collection
        courses_coll = get_courses_collection()
        skill_query = f"courses for {' '.join(job_requirements[:5])} skills development"
        course_results = search_collection(courses_coll, skill_query, n_results=5)
        if course_results:
            courses_context = "Available courses:\n" + "\n".join(
                f"- {r['document']}" for r in course_results
            )
    except Exception as exc:
        debug(f"Market Intel: courses RAG error: {exc}")

    # RAG: query trends collection
    trends_context = ""
    try:
        from vectordb.collections import get_trends_collection
        trends_coll = get_trends_collection()
        trend_results = search_collection(trends_coll, job_query, n_results=4)
        if trend_results:
            trends_context = "Industry trends:\n" + "\n".join(
                f"- {r['document']}" for r in trend_results
            )
    except Exception as exc:
        debug(f"Market Intel: trends RAG error: {exc}")

    # Salary lookup
    salary_insights = _lookup_salary(job_query, years_exp)

    # LLM analysis
    user_prompt = (
        f"Candidate skills: {', '.join(candidate_skills)}\n"
        f"Years of experience: {years_exp or 'Unknown'}\n"
        f"Target job requirements (from top matches): {', '.join(job_requirements)}\n"
        f"Job query: {job_query}\n\n"
        f"{courses_context}\n\n"
        f"{trends_context}\n\n"
        f"Salary data: {json.dumps(salary_insights) if salary_insights else 'Not available'}\n\n"
        f"Analyze skill gaps, create upskilling roadmap, provide salary insights and industry trends."
    )

    try:
        llm = ChatOpenAI(model=settings.default_model, temperature=0)
        response = llm.invoke([
            SystemMessage(content=MARKET_INTELLIGENCE_SYSTEM),
            HumanMessage(content=user_prompt),
        ])
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
    }

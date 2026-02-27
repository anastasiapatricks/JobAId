"""Job Discovery & Matching agent — merges job search + relevance scoring.

Uses Adzuna API (with MOCK_JOBS fallback), ChromaDB semantic matching,
and LLM-powered ranking with scoring rubric.
"""

import json
from typing import Dict, Any, List

from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

from config.settings import settings
from config.prompts import JOB_DISCOVERY_SYSTEM
from tools.job_board_api import search_jobs
from tools.chromadb_tools import upsert_jobs, search_collection
from utils import debug


def _parse_json_response(text: str) -> Any:
    """Extract JSON from LLM response."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        debug(f"Job Discovery JSON parse failed: {text[:200]}")
        return []


def _build_resume_summary(state: Dict[str, Any]) -> str:
    """Build a text summary of the candidate from resume_info."""
    info = state.get("resume_debiased") or state.get("resume_info") or {}
    parts = []

    skills = info.get("skills", {})
    if isinstance(skills, dict):
        tech = skills.get("technical", [])
        if tech:
            parts.append(f"Technical skills: {', '.join(tech)}")
        soft = skills.get("soft", [])
        if soft:
            parts.append(f"Soft skills: {', '.join(soft)}")
    elif isinstance(skills, list):
        parts.append(f"Skills: {', '.join(skills)}")

    yoe = info.get("years_of_experience")
    if yoe:
        parts.append(f"Years of experience: {yoe}")

    summary = info.get("professional_summary")
    if summary:
        parts.append(f"Summary: {summary}")

    experience = info.get("experience", [])
    if experience:
        titles = [e.get("title", "") for e in experience if e.get("title")]
        if titles:
            parts.append(f"Previous roles: {', '.join(titles[:3])}")

    return "\n".join(parts) if parts else "No resume information available."


def _fallback_score(resume_info: dict, job: dict) -> dict:
    """Compute a basic skill-overlap score when LLM ranking fails."""
    skills = resume_info.get("skills", {})
    if isinstance(skills, dict):
        skill_list = skills.get("technical", []) + skills.get("soft", [])
    elif isinstance(skills, list):
        skill_list = skills
    else:
        skill_list = []

    sset = {s.lower() for s in skill_list}
    kws = {k.lower() for k in job.get("keywords", [])}
    overlap = sorted(sset & kws)
    score = min(int(len(overlap) * 15), 100)

    return {
        "title": job.get("title", ""),
        "company": job.get("company", ""),
        "location": job.get("location", ""),
        "score": score,
        "explanation": f"Skill overlap: {', '.join(overlap)}" if overlap else "No direct skill overlap found",
        "keywords": job.get("keywords", []),
        "url": job.get("url", ""),
        "source": job.get("source", "mock"),
    }


def job_discovery(state: Dict[str, Any]) -> Dict[str, Any]:
    """Run the Job Discovery & Matching pipeline.

    Steps:
    1. Search for jobs via Adzuna API (fallback to MOCK_JOBS)
    2. Upsert job listings into ChromaDB for semantic matching
    3. Use LLM to rank and score jobs against candidate profile
    """
    job_query = state.get("job_query", "")
    location = state.get("location_preference", "")
    resume_info = state.get("resume_debiased") or state.get("resume_info") or {}

    # Step 1: Search for jobs
    debug(f"Job Discovery: searching for '{job_query}'")
    raw_jobs = search_jobs(job_query, location)

    if not raw_jobs:
        return {
            "messages": [{"role": "assistant", "content": "[Job Discovery] No jobs found matching your query."}],
            "job_listings": [],
            "scored_jobs": [],
            "fallback_used": list(state.get("fallback_used") or []) + ["no_jobs_found"],
        }

    # Track data source
    source = raw_jobs[0].get("source", "mock")
    fallback_used = list(state.get("fallback_used") or [])
    if source == "mock":
        fallback_used.append("mock_jobs")

    # Step 2: Upsert into ChromaDB for semantic search
    try:
        from vectordb.collections import get_jobs_collection
        jobs_collection = get_jobs_collection()
        upsert_jobs(jobs_collection, raw_jobs)

        # Semantic search with resume summary
        resume_summary = _build_resume_summary(state)
        semantic_results = search_collection(jobs_collection, resume_summary, n_results=min(len(raw_jobs), 10))
        debug(f"Job Discovery: semantic search returned {len(semantic_results)} results")
    except Exception as exc:
        debug(f"Job Discovery: ChromaDB error (non-fatal): {exc}")
        semantic_results = []

    # Step 3: LLM ranking
    resume_summary = _build_resume_summary(state)
    jobs_text = json.dumps([
        {"title": j.get("title"), "company": j.get("company"), "location": j.get("location"),
         "keywords": j.get("keywords", []), "description": j.get("description", "")[:200],
         "url": j.get("url", "")}
        for j in raw_jobs
    ], indent=2)

    user_prompt = (
        f"Candidate profile:\n{resume_summary}\n\n"
        f"Job query: {job_query}\n"
        f"Location preference: {location or 'Any'}\n\n"
        f"Job listings:\n{jobs_text}\n\n"
        f"Score and rank these jobs for this candidate."
    )

    try:
        llm = ChatOpenAI(model=settings.default_model, temperature=0)
        response = llm.invoke([
            SystemMessage(content=JOB_DISCOVERY_SYSTEM),
            HumanMessage(content=user_prompt),
        ])
        scored = _parse_json_response(response.content)
        if isinstance(scored, list) and scored:
            # Build lookup to recover URLs the LLM may have dropped
            url_lookup = {}
            for j in raw_jobs:
                key = (j.get("title", "").lower().strip(), j.get("company", "").lower().strip())
                if j.get("url"):
                    url_lookup[key] = j["url"]

            # Ensure all required fields
            for item in scored:
                item.setdefault("source", source)
                item.setdefault("keywords", [])
                # Recover URL from raw jobs if the LLM dropped it
                if not item.get("url"):
                    key = (item.get("title", "").lower().strip(), item.get("company", "").lower().strip())
                    item["url"] = url_lookup.get(key, "")
            scored.sort(key=lambda x: -x.get("score", 0))
        else:
            raise ValueError("LLM returned empty or non-list response")
    except Exception as exc:
        debug(f"Job Discovery: LLM ranking failed ({exc}), using fallback scoring")
        scored = [_fallback_score(resume_info, j) for j in raw_jobs]
        scored.sort(key=lambda x: -x.get("score", 0))
        fallback_used.append("fallback_scoring")

    top5 = scored[:5]
    explanations = [f"{j.get('title')} @ {j.get('company')}: {j.get('explanation', '')}" for j in top5]

    # Build display message
    lines = [
        f"{i+1}. {j.get('title', '?')} @ {j.get('company', '?')} — {j.get('score', '?')}/100"
        for i, j in enumerate(top5)
    ]
    msg = f"[Job Discovery] Found {len(raw_jobs)} jobs, ranked top {len(top5)}:\n" + "\n".join(lines)

    return {
        "messages": [{"role": "assistant", "content": msg}],
        "job_listings": raw_jobs,
        "scored_jobs": scored,
        "matching_explanation": explanations,
        "fallback_used": fallback_used,
    }

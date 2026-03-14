"""Job Discovery & Matching agent — merges job search + relevance scoring.

Uses Adzuna API (with MOCK_JOBS fallback), ChromaDB semantic matching,
and LLM-powered ranking with scoring rubric.
"""

import json
from typing import Dict, Any, List

from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

import logging

from config.settings import settings
from config.prompts import JOB_DISCOVERY_SYSTEM
from guardrails.input_filter import validate_job_query, spotlight_wrap
from guardrails.output_filter import validate_job_discovery_output
from guardrails.model_router import get_model_for_task
from tools.job_board_api import search_jobs
from tools.chromadb_tools import upsert_jobs, search_collection
from utils import debug, get_latest_results
from utils.llm_logger import logged_invoke

_guard_logger = logging.getLogger("jobaid.guardrails")


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
    latest = get_latest_results(state)
    info = latest.get("resume_debiased") or state.get("resume_debiased") or latest.get("resume_info") or state.get("resume_info") or {}
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
        "description": job.get("description", ""),
        "url": job.get("url", ""),
        "salary_min": job.get("salary_min"),
        "salary_max": job.get("salary_max"),
        "created_at": job.get("created_at"),
        "category": job.get("category"),
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

    # Input validation
    valid, error_msg = validate_job_query(job_query)
    if not valid:
        return {
            "messages": [{"role": "assistant", "content": f"[Job Discovery] {error_msg}"}],
            "job_listings": [],
            "scored_jobs": [],
            "errors": list(state.get("errors") or []) + [{"stage": "discovery", "error": error_msg}],
        }

    latest = get_latest_results(state)
    resume_info = latest.get("resume_debiased") or state.get("resume_debiased") or latest.get("resume_info") or state.get("resume_info") or {}

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
    
    # Add temporary IDs for robust recovery
    for i, j in enumerate(raw_jobs):
        j["_ref_id"] = f"job_{i}"

    jobs_text = json.dumps([
        {"ref_id": j["_ref_id"], "title": j.get("title"), "company": j.get("company"), 
         "location": j.get("location"), "keywords": j.get("keywords", []), 
         "description": j.get("description", "")[:250], "url": j.get("url", ""), 
         "salary_min": j.get("salary_min"), "salary_max": j.get("salary_max"),
         "created_at": j.get("created_at"), "category": j.get("category")}
        for j in raw_jobs
    ], indent=2)

    user_prompt = (
        f"Candidate profile:\n{resume_summary}\n\n"
        f"Job query: {spotlight_wrap(job_query)}\n"
        f"Location preference: {location or 'Any'}\n\n"
        f"Job listings:\n{jobs_text}\n\n"
        f"Score and rank these jobs for this candidate. Include the 'ref_id' for each job in your response."
    )

    try:
        from agents.orchestrator import get_autonomy
        if not get_autonomy().record_llm_call():
            raise RuntimeError("LLM call limit exceeded")
        llm = ChatOpenAI(model=get_model_for_task("job_ranking"), temperature=0)
        response = logged_invoke(llm, [
            SystemMessage(content=JOB_DISCOVERY_SYSTEM),
            HumanMessage(content=user_prompt),
        ], "job_ranking")
        scored = _parse_json_response(response.content)
        if isinstance(scored, list) and scored:
            # Ensure all required fields
            for item in scored:
                item.setdefault("source", source)
                item.setdefault("keywords", [])
                
                # Recover full data from raw jobs using ref_id (preferred) or fuzzy match
                matching_raw = None
                ref_id = item.get("ref_id") or item.get("id")
                if ref_id:
                    # Search by ref_id
                    matching_raw = next((j for j in raw_jobs if j.get("_ref_id") == ref_id), None)
                    if not matching_raw and isinstance(ref_id, (int, str)):
                        # Fallback for int IDs if LLM stripped prefix
                        try:
                            idx = int(str(ref_id).replace("job_", ""))
                            if 0 <= idx < len(raw_jobs):
                                matching_raw = raw_jobs[idx]
                        except (ValueError, TypeError):
                            pass
                
                if not matching_raw:
                    # Fallback to key-based match
                    title = item.get("title", "").lower().strip()
                    company = item.get("company", "").lower().strip()
                    matching_raw = next((j for j in raw_jobs if j.get("title", "").lower().strip() == title and j.get("company", "").lower().strip() == company), None)
                
                if matching_raw:
                    # Overwrite/Set all critical fields from raw source to ensure data integrity
                    item["url"] = matching_raw.get("url") or item.get("url") or ""
                    item["description"] = matching_raw.get("description") or item.get("description") or ""
                    item["company"] = matching_raw.get("company") or item.get("company") or ""
                    item["title"] = matching_raw.get("title") or item.get("title") or ""
                    item["location"] = matching_raw.get("location") or item.get("location") or ""
                    item["salary_min"] = matching_raw.get("salary_min")
                    item["salary_max"] = matching_raw.get("salary_max")
                    item["created_at"] = matching_raw.get("created_at")
                    item["category"] = matching_raw.get("category")
                    # Preserve keywords from raw source for skill triage
                    if matching_raw.get("keywords"):
                        item["keywords"] = matching_raw["keywords"]
                
                item.setdefault("url", "")
            debug(f"Job Discovery: recovered details for {len([i for i in scored if i.get('url')])} jobs")
            scored.sort(key=lambda x: -x.get("score", 0))
        else:
            raise ValueError("LLM returned empty or non-list response")
    except Exception as exc:
        debug(f"Job Discovery: LLM ranking failed ({exc}), using fallback scoring")
        scored = [_fallback_score(resume_info, j) for j in raw_jobs]
        scored.sort(key=lambda x: -x.get("score", 0))
        fallback_used.append("fallback_scoring")

    top10 = scored[:10]
    explanations = [f"{j.get('title')} @ {j.get('company')}: {j.get('explanation', '')}" for j in top10]

    lines = [
        f"{i+1}. {j.get('title', '?')} @ {j.get('company', '?')} — {j.get('score', '?')}/100"
        for i, j in enumerate(top10)
    ]
    msg = f"[Job Discovery] Found {len(raw_jobs)} jobs, ranked top {len(top10)}:\n" + "\n".join(lines)

    result = {
        "messages": [{"role": "assistant", "content": msg}],
        "job_listings": raw_jobs,
        "scored_jobs": top10,
        "matching_explanation": explanations,
        "fallback_used": fallback_used,
    }

    valid, issues = validate_job_discovery_output(result)
    if not valid:
        _guard_logger.warning(f"Job discovery output validation issues: {issues}")

    return result

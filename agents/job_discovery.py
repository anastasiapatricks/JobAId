"""Job Discovery & Matching agent — merges job search + relevance scoring.

Uses Adzuna API (with MOCK_JOBS fallback), ChromaDB semantic matching,
and LLM-powered ranking with scoring rubric.
"""

import json
from typing import Dict, Any, List

from langchain_core.messages import SystemMessage, HumanMessage

import logging

from config.settings import settings
from config.prompts import JOB_DISCOVERY_SYSTEM, JOB_DISCOVERY_PROMPT_VERSION
from xai.trace import create_trace
from xai.explainers import shap_skill_attribution, lime_job_explanation
from xai.fairness import statistical_parity_check, equal_opportunity_check
from guardrails.input_filter import validate_job_query, spotlight_wrap
from guardrails.output_filter import validate_job_discovery_output
from guardrails.model_router import get_model_for_task
from guardrails.llm_factory import get_llm
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

    # Step 1: Search for jobs — use multiple query variations for broader coverage
    debug(f"Job Discovery: searching for '{job_query}'")
    raw_jobs = search_jobs(job_query, location, num_results=15)

    # Also search with domain context from the resume to catch relevant
    # jobs that Adzuna misses with the literal query alone
    summary_text = (resume_info.get("professional_summary") or "").lower()
    domain_terms = []
    for term in ["cybersecurity", "security", "data science", "software engineering",
                  "finance", "marketing", "healthcare"]:
        if term in summary_text and term not in job_query.lower():
            domain_terms.append(term)
    if domain_terms:
        augmented_query = f"{job_query} {domain_terms[0]}"
        debug(f"Job Discovery: augmented search '{augmented_query}'")
        extra_jobs = search_jobs(augmented_query, location, num_results=10)
        # Deduplicate by title + company
        seen = {(j.get("title", "").lower(), j.get("company", "").lower()) for j in raw_jobs}
        for j in extra_jobs:
            key = (j.get("title", "").lower(), j.get("company", "").lower())
            if key not in seen:
                raw_jobs.append(j)
                seen.add(key)

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
        llm = get_llm(model=get_model_for_task("job_ranking"), temperature=0, task_type="job_ranking")
        response = logged_invoke(llm, [
            SystemMessage(content=JOB_DISCOVERY_SYSTEM),
            HumanMessage(content=user_prompt),
        ], "job_ranking")
        scored = _parse_json_response(response.content)
        # If LLM returned empty (all jobs irrelevant), retry with resume job title
        if not (isinstance(scored, list) and scored):
            exp = resume_info.get("experience", [])
            job_title = (resume_info.get("desired_job_title") or resume_info.get("current_title")
                         or (exp[0].get("title") if exp else "") or "")
            if job_title and job_title.lower() != job_query.lower():
                debug(f"Job Discovery: LLM scored nothing, retrying with resume title '{job_title}'")
                retry_jobs = search_jobs(job_title, location, num_results=15)
                if retry_jobs and retry_jobs[0].get("source") != "mock":
                    raw_jobs = retry_jobs
                    source = "adzuna"
                    # rebuild jobs_text and re-ask
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
                    user_prompt2 = (
                        f"Candidate profile:\n{resume_summary}\n\n"
                        f"Job query: {spotlight_wrap(job_title)}\n"
                        f"Location preference: {location or 'Any'}\n\n"
                        f"Job listings:\n{jobs_text}\n\n"
                        f"Score and rank these jobs for this candidate. Include the 'ref_id' for each job in your response."
                    )
                    response2 = logged_invoke(llm, [
                        SystemMessage(content=JOB_DISCOVERY_SYSTEM),
                        HumanMessage(content=user_prompt2),
                    ], "job_ranking")
                    scored = _parse_json_response(response2.content)
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

    # Quality check: if Adzuna returned irrelevant results, auto-retry with resume title
    avg_top3 = sum(j.get("score", 0) for j in top10[:3]) / max(len(top10[:3]), 1)
    if avg_top3 < 25 and resume_info:
        exp = resume_info.get("experience", [])
        resume_title = (
            resume_info.get("desired_job_title")
            or resume_info.get("current_title")
            or (exp[0].get("title") if exp else "")
            or ""
        )
        if resume_title and resume_title.lower() not in job_query.lower():
            debug(f"Job Discovery: low quality results (avg={avg_top3:.0f}), retrying with resume title '{resume_title}'")
            retry_raw = search_jobs(resume_title, location, num_results=15)
            if retry_raw:
                for i, j in enumerate(retry_raw):
                    j["_ref_id"] = f"retry_{i}"
                retry_text = json.dumps([
                    {"ref_id": j["_ref_id"], "title": j.get("title"), "company": j.get("company"),
                     "location": j.get("location"), "keywords": j.get("keywords", []),
                     "description": j.get("description", "")[:250], "url": j.get("url", "")}
                    for j in retry_raw
                ], indent=2)
                try:
                    retry_resp = logged_invoke(llm, [
                        SystemMessage(content=JOB_DISCOVERY_SYSTEM),
                        HumanMessage(content=(
                            f"Candidate profile:\n{resume_summary}\n\n"
                            f"Job query: {spotlight_wrap(resume_title)}\n"
                            f"Location: {location or 'Any'}\n\n"
                            f"Job listings:\n{retry_text}\n\n"
                            f"Score and rank these jobs. Include ref_id for each."
                        )),
                    ], "job_ranking_retry")
                    retry_scored = _parse_json_response(retry_resp.content)
                    if isinstance(retry_scored, list) and retry_scored:
                        retry_avg = sum(j.get("score", 0) for j in retry_scored[:3]) / max(len(retry_scored[:3]), 1)
                        if retry_avg > avg_top3:
                            debug(f"Job Discovery: retry improved avg score {avg_top3:.0f} → {retry_avg:.0f}")
                            for item in retry_scored:
                                item.setdefault("source", retry_raw[0].get("source", "adzuna"))
                                ref = item.get("ref_id") or ""
                                match = next((j for j in retry_raw if j.get("_ref_id") == ref), None)
                                if not match:
                                    title_k = item.get("title", "").lower()
                                    match = next((j for j in retry_raw if j.get("title", "").lower() == title_k), None)
                                if match:
                                    for f in ("url", "description", "company", "title", "location",
                                              "salary_min", "salary_max", "created_at", "category", "keywords"):
                                        if match.get(f):
                                            item[f] = match[f]
                            retry_scored.sort(key=lambda x: -x.get("score", 0))
                            scored = retry_scored
                            top10 = scored[:10]
                            raw_jobs = retry_raw
                            avg_top3 = retry_avg
                            fallback_used.append("query_reformulated")
                except Exception as e:
                    debug(f"Job Discovery: retry failed ({e})")

    # Determine result quality for the chat message
    if avg_top3 >= 50:
        quality = "good"
    elif avg_top3 >= 25:
        quality = "fair"
    else:
        quality = "poor"

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
        "result_quality": quality,
        "original_query": job_query,
    }

    valid, issues = validate_job_discovery_output(result)
    if not valid:
        from datetime import datetime, timezone
        _guard_logger.warning(json.dumps({
            "event": "guardrail_triggered",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "guardrail": "output_validation",
            "agent": "job_discovery",
            "issues": issues,
        }))

    # --- XAI: Build comprehensive candidate skill list ---
    # Include parsed skills + domain terms from resume text so SHAP/LIME
    # can match against domain-level job keywords like "incident response"
    candidate_skills_raw = resume_info.get("skills", {})
    if isinstance(candidate_skills_raw, dict):
        candidate_skill_list = (
            candidate_skills_raw.get("technical", [])
            + candidate_skills_raw.get("soft", [])
            + candidate_skills_raw.get("certifications", [])
        )
    elif isinstance(candidate_skills_raw, list):
        candidate_skill_list = candidate_skills_raw
    else:
        candidate_skill_list = []

    # Extract domain terms from resume summary + experience descriptions
    # so we match "incident response", "malware analysis" etc., not just tool names
    _resume_full = resume_info or {}
    _resume_text_parts = [
        _resume_full.get("professional_summary") or "",
        " ".join(
            (e.get("description") or "") for e in _resume_full.get("experience", [])
            if isinstance(e, dict)
        ),
    ]
    _resume_text = " ".join(_resume_text_parts)
    if _resume_text.strip():
        try:
            from tools.job_board_api import _extract_keywords_from_text
            _domain_terms = _extract_keywords_from_text(_resume_text)
            # Add domain terms not already in skill list
            _existing_lower = {s.lower() for s in candidate_skill_list}
            for term in _domain_terms:
                if term.lower() not in _existing_lower:
                    candidate_skill_list.append(term)
        except ImportError:
            pass

    shap_attributions = {}
    for job in top10[:5]:
        job_key = f"{job.get('title', '?')} @ {job.get('company', '?')}"
        shap_attributions[job_key] = shap_skill_attribution(
            candidate_skill_list,
            job.get("keywords", []),
            job_description=f"{job.get('title', '')} {job.get('description', '')}",
        )
    result["shap_attributions"] = shap_attributions

    # --- XAI: LIME-like explanation for the top job ---
    lime_explanations = []
    if top10:
        top_job = top10[0]
        lime_explanations = lime_job_explanation(
            candidate_skill_list,
            top_job.get("keywords", []),
            top_n=5,
            job_description=f"{top_job.get('title', '')} {top_job.get('description', '')}",
        )
    result["lime_explanations"] = lime_explanations

    # --- XAI: Fairness audit ---
    candidate_location = state.get("location_preference", "")
    result["fairness_audit"] = {
        "statistical_parity": statistical_parity_check(top10, candidate_location),
        "equal_opportunity": equal_opportunity_check(top10, candidate_location),
    }

    # --- XAI: Explainability trace ---
    xai_warnings = list(fallback_used)

    # Derive grounding_score from SHAP overlap metadata for the top job
    _grounding = 0.0
    if top10:
        _top_key = f"{top10[0].get('title', '?')} @ {top10[0].get('company', '?')}"
        _top_shap = shap_attributions.get(_top_key, {})
        _meta = _top_shap.get("_meta", {})
        _kw_count = _meta.get("keyword_count", 0) if isinstance(_meta, dict) else 0
        _overlap = _meta.get("overlap_count", 0) if isinstance(_meta, dict) else 0
        _grounding = round(_overlap / max(_kw_count, 1), 4) if _kw_count > 0 else 0.0

    result["explainability_trace"] = create_trace(
        agent_name="job_discovery",
        prompt_version=JOB_DISCOVERY_PROMPT_VERSION,
        confidence=top10[0].get("score", 0) / 100.0 if top10 else 0.0,
        grounding_score=_grounding,
        reasoning=f"Ranked {len(top10)} jobs from {len(raw_jobs)} candidates; source={source}",
        feature_attributions={"top_job_shap": shap_attributions.get(
            f"{top10[0].get('title', '?')} @ {top10[0].get('company', '?')}", {}
        ) if top10 else {}},
        sources_consulted=[source, "chromadb"] if semantic_results else [source],
        warnings=xai_warnings,
    ).to_dict()

    return result

"""Pitch Generator — 4-step prompt chaining for cover letter generation."""

from typing import Dict, Any
import json
import re
from datetime import datetime, timezone

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

import logging

from config.settings import settings
from config.prompts import (
    PITCH_RESEARCH_SYSTEM,
    PITCH_MATCH_ANALYSIS_SYSTEM,
    PITCH_DRAFT_SYSTEM,
    PITCH_REVIEW_SYSTEM,
    PITCH_GENERATOR_PROMPT_VERSION,
)
from xai.trace import create_trace
from xai.grounding import verify_pitch_grounding
from guardrails.output_filter import (
    validate_pitch_output,
    check_pitch_pii_leakage,
    check_pitch_professionalism,
    check_pitch_grounding,
    check_pitch_fabrication,
)
from guardrails.input_filter import sanitize_pitch_input, validate_pitch_job_data
from guardrails.model_router import get_model_for_task
from tools.tavily_search import search_company, search_company_contact
from tools.wikipedia import get_company_summary
from tools.chromadb_tools import search_collection
from vectordb.collections import get_cover_letters_collection
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
    """Get the selected or top-scored job from state."""
    selected = state.get("_selected_job")
    if selected:
        return selected
    latest = get_latest_results(state)
    scored = state.get("scored_jobs") or latest.get("scored_jobs") or []
    if scored:
        return scored[0]
    listings = latest.get("job_listings") or state.get("job_listings") or []
    if listings:
        return listings[0]
    return {}


def _build_candidate_summary(state: Dict[str, Any]) -> str:
    """Build a text summary of the candidate.

    PII (name, email, phone) is intentionally excluded to prevent leakage
    to the LLM. These are populated via post-processing on the final output.
    """
    latest = get_latest_results(state)
    info = latest.get("resume_info") or state.get("resume_info") or {}
    parts = []

    # NOTE: candidate name, email, phone are NOT included here (PII protection).
    # They are populated via _replace_placeholders() after LLM generation.

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


def _get_candidate_contact(state: Dict[str, Any]) -> Dict[str, str]:
    """Extract candidate contact info from state (for post-processing only, never sent to LLM)."""
    latest = get_latest_results(state)
    info = latest.get("resume_info") or state.get("resume_info") or {}
    contact = info.get("contact_info", {}) if isinstance(info, dict) else {}
    if not isinstance(contact, dict):
        contact = {}
    return {
        "name": contact.get("name", ""),
        "email": contact.get("email", ""),
        "phone": contact.get("phone", ""),
    }


def _replace_placeholders(
    text: str,
    candidate_contact: Dict[str, str],
    company: str,
    location: str,
    company_contact: Dict[str, str],
) -> str:
    """Replace bracket placeholders with actual candidate and company data.

    Candidate PII is populated here (never sent to the LLM).
    Company details are populated as a fallback if the LLM missed them.
    """
    # Candidate PII replacements (from state, never sent to LLM)
    candidate_replacements = {
        r"\[Candidate Name\]": candidate_contact.get("name", ""),
        r"\[Your Name\]": candidate_contact.get("name", ""),
        r"\[Candidate Email\]": candidate_contact.get("email", ""),
        r"\[Your Email\]": candidate_contact.get("email", ""),
        r"\[Email\]": candidate_contact.get("email", ""),
        r"\[Candidate Phone\]": candidate_contact.get("phone", ""),
        r"\[Your Phone\]": candidate_contact.get("phone", ""),
        r"\[Your Phone Number\]": candidate_contact.get("phone", ""),
    }

    # Company data replacements (fallback if LLM still used placeholders)
    company_addr = company_contact.get("office_address", "")
    company_phone = company_contact.get("phone", "")
    company_city = company_contact.get("city", "")
    # Treat "Not available" as empty
    if company_addr.lower() == "not available":
        company_addr = ""
    if company_phone.lower() == "not available":
        company_phone = ""
    if company_city.lower() == "not available":
        company_city = ""

    company_replacements = {
        r"\[Company Name\]": company,
        r"\[Company Address\]": company_addr,
        r"\[Company Phone\]": company_phone,
        r"\[Address\]": company_addr,
        r"\[City,?\s*State,?\s*Zip\]": company_city or location,
        r"\[City,?\s*State\s*Zip\s*Code\]": company_city or location,
        r"\[City\]": company_city or location,
        r"\[Phone Number\]": company_phone,
        r"\[Phone\]": company_phone,
        r"\[Hiring Manager Name\]": "Hiring Manager",
        r"\[Hiring Manager\]": "Hiring Manager",
        r"\[Recipient Name\]": "Hiring Manager",
        r"\[Date\]": datetime.now().strftime("%B %d, %Y"),
    }

    for pattern, replacement in {**candidate_replacements, **company_replacements}.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    # Safety net: remove any remaining [Bracketed Placeholder] patterns
    text = re.sub(r"\[[A-Z][A-Za-z, ]{2,30}\]", "", text)

    # Clean up blank lines left by removed placeholders
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def pitch_generator(state: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a cover letter through 4-step prompt chaining.

    1. Company research (Wikipedia + job details)
    2. Match analysis (candidate-job fit)
    3. Draft generation
    4. Quality review
    """
    best_job = _get_best_job(state)
    generic_mode = not best_job

    from agents.orchestrator import get_autonomy
    candidate_summary = _build_candidate_summary(state)
    llm = ChatOpenAI(model=get_model_for_task("pitch_draft"), temperature=0.7)

    draft_pitches = []

    if generic_mode:
        # ─── Generic mode: no specific job, generate from resume alone ───
        debug("Pitch Generator: generic mode — no job targeted")
        company = ""
        job_title = ""
        job_location = ""
        company_research = ""
        company_contact = {}
        job_context = "No specific job targeted. Write a general-purpose cover letter for the candidate's field."
    else:
        # ─── Job-specific mode ───
        # ─── Sanitize job listing data (indirect injection defense) ───
        best_job, job_safe, job_warnings = validate_pitch_job_data(best_job)
        if job_warnings:
            debug(f"Pitch Generator: job data sanitized — {job_warnings}")

        company = best_job.get("company", "")
        job_title = best_job.get("title", "the role")
        job_location = best_job.get("location", "")

        # ─── Step 1: Company Research ───
        debug("Pitch Generator: Step 1 — company research")
        company_info = ""
        company_contact_info = ""
        if company:
            try:
                company_info = search_company(company)
            except Exception as exc:
                debug(f"Pitch Generator: Tavily company search error: {exc}")
            if not company_info:
                debug("Pitch Generator: Tavily company search empty, falling back to Wikipedia")
                try:
                    company_info = get_company_summary(company)
                except Exception as exc:
                    debug(f"Pitch Generator: Wikipedia error: {exc}")
                    company_info = f"{company} is a technology company."

            # Search for company contact info (address, phone) for the job's region
            try:
                company_contact_info = search_company_contact(company, job_location)
            except Exception as exc:
                debug(f"Pitch Generator: Tavily company contact search error: {exc}")

        # ─── Sanitize external research content (indirect injection defense) ───
        if company_info:
            company_info, research_safe, research_detail = sanitize_pitch_input(
                company_info, "company_research"
            )
            if not research_safe:
                debug(f"Pitch Generator: company research sanitized — {research_detail}")

        if company_contact_info:
            company_contact_info, contact_safe, contact_detail = sanitize_pitch_input(
                company_contact_info, "company_contact"
            )
            if not contact_safe:
                debug(f"Pitch Generator: company contact info sanitized — {contact_detail}")

        job_context = (
            f"Company: {company}\n"
            f"Job title: {job_title}\n"
            f"Location: {job_location or 'N/A'}\n"
            f"Job keywords: {', '.join(best_job.get('keywords', []))}\n"
            f"Job description: {best_job.get('description', 'N/A')[:500]}\n"
        )

        research_input = f"{job_context}\n\nCompany info:\n{company_info}"
        if company_contact_info:
            research_input += f"\n\nCompany contact info:\n{company_contact_info}"

        if not get_autonomy().record_llm_call():
            raise RuntimeError("LLM call limit exceeded")
        research_response = logged_invoke(llm, [
            SystemMessage(content=PITCH_RESEARCH_SYSTEM),
            HumanMessage(content=research_input),
        ], "pitch_research")

        # Parse structured research response (JSON with summary + contact_info)
        research_parsed = _parse_json_response(research_response.content)
        if research_parsed and "summary" in research_parsed:
            company_research = research_parsed["summary"]
            company_contact = research_parsed.get("contact_info", {})
            if not isinstance(company_contact, dict):
                company_contact = {}
            debug(f"Pitch Generator: extracted company contact: {company_contact}")
        else:
            # Fallback: treat entire response as prose summary (no structured contact)
            company_research = research_response.content
            company_contact = {}
            debug("Pitch Generator: research response was not structured JSON, using as prose")

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

    # Retrieve relevant cover letter samples from RAG
    samples_context = ""
    try:
        cover_letters_coll = get_cover_letters_collection()
        if generic_mode:
            # Use candidate's field/skills for RAG query
            sample_query = f"cover letter {candidate_summary[:100]}"
        else:
            keywords = best_job.get("keywords", [])
            sample_query = f"cover letter for {job_title} {keywords[0] if keywords else ''}"
        sample_results = search_collection(cover_letters_coll, sample_query, n_results=3)
        if sample_results:
            samples_parts = []
            for j, res in enumerate(sample_results, 1):
                meta = res.get("metadata", {})
                samples_parts.append(
                    f"--- Sample {j} (Industry: {meta.get('industry', 'N/A')}, "
                    f"Level: {meta.get('experience_level', 'N/A')}) ---\n"
                    f"{res['document']}"
                )
            samples_context = (
                "Reference cover letter samples (use as style/structure guide, do NOT copy):\n\n"
                + "\n\n".join(samples_parts)
            )
            debug(f"Pitch Generator: Retrieved {len(sample_results)} cover letter samples from RAG")
    except Exception as exc:
        debug(f"Pitch Generator: Cover letter RAG retrieval error: {exc}")

    # Build company contact context for the draft prompt
    contact_context = ""
    if company_contact:
        contact_parts = []
        for key in ("office_address", "phone", "city"):
            val = company_contact.get(key, "")
            if val and val.lower() != "not available":
                contact_parts.append(f"  {key}: {val}")
        if contact_parts:
            contact_context = "Company contact details (use these in the letter header):\n" + "\n".join(contact_parts) + "\n\n"

    if generic_mode:
        draft_prompt = (
            f"Write a general-purpose cover letter for this candidate.\n\n"
            f"Candidate:\n{candidate_summary}\n\n"
            f"Match analysis:\n{json.dumps(match_analysis, indent=2)}\n\n"
            + (f"{samples_context}\n\n" if samples_context else "")
            + "Write a compelling, general-purpose cover letter that showcases the candidate's strengths."
        )
    else:
        draft_prompt = (
            f"Write a cover letter for this candidate applying to {job_title} at {company}.\n\n"
            f"Candidate:\n{candidate_summary}\n\n"
            f"Company research:\n{company_research}\n\n"
            + contact_context
            + f"Match analysis:\n{json.dumps(match_analysis, indent=2)}\n\n"
            + (f"{samples_context}\n\n" if samples_context else "")
            + "Write a compelling, personalized cover letter."
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

    # Provide context so reviewer can verify company details are real
    if generic_mode:
        review_context = "\n\nContext — This is a general-purpose cover letter, not targeting a specific company."
    else:
        review_context = (
            f"\n\nContext — Company: {company}, Location: {job_location}"
        )
        if company_contact:
            review_context += f", Contact: {json.dumps(company_contact)}"

    review_response = logged_invoke(review_llm, [
        SystemMessage(content=PITCH_REVIEW_SYSTEM),
        HumanMessage(content=f"Review and improve this cover letter:\n\n{draft}{review_context}"),
    ], "pitch_review")
    raw_final_pitch = review_response.content
    draft_pitches.append({"version": "final", "content": raw_final_pitch})

    # ─── Guardrail checks (on raw LLM output, BEFORE post-processing) ───
    all_issues = []

    # Build temporary result for structural validation
    temp_result = {"final_pitch": raw_final_pitch, "draft_pitches": draft_pitches}
    valid, issues = validate_pitch_output(temp_result)
    if not valid:
        all_issues.extend(issues)

    if raw_final_pitch:
        # PII leakage check — on raw output to catch LLM leaking PII
        pii_ok, pii_issues = check_pitch_pii_leakage(raw_final_pitch)
        if not pii_ok:
            all_issues.extend(pii_issues)

        # Professionalism check
        prof_ok, prof_issues = check_pitch_professionalism(raw_final_pitch)
        if not prof_ok:
            all_issues.extend(prof_issues)

        # Grounding check — verify pitch uses actual candidate skills
        info = state.get("resume_info") or {}
        skills_data = info.get("skills", {})
        candidate_skills = []
        if isinstance(skills_data, dict):
            candidate_skills = skills_data.get("technical", [])
        elif isinstance(skills_data, list):
            candidate_skills = skills_data
        contact_info = info.get("contact_info", {})
        cand_name = contact_info.get("name") if isinstance(contact_info, dict) else None

        grounding_score, grounding_warnings = check_pitch_grounding(
            raw_final_pitch, candidate_skills, cand_name
        )
        if grounding_warnings:
            all_issues.extend(grounding_warnings)

        # Fabrication check
        fab_ok, fab_issues = check_pitch_fabrication(raw_final_pitch)
        if not fab_ok:
            all_issues.extend(fab_issues)

    if all_issues:
        _guard_logger.warning(json.dumps({
            "event": "guardrail_triggered",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "guardrail": "pitch_output_validation",
            "agent": "pitch_generator",
            "issues": all_issues,
        }))

    # ─── Post-processing: replace placeholders with actual data ───
    candidate_contact = _get_candidate_contact(state)
    final_pitch = _replace_placeholders(
        raw_final_pitch,
        candidate_contact=candidate_contact,
        company=company,
        location=job_location,
        company_contact=company_contact,
    )
    debug("Pitch Generator: post-processing completed — placeholders replaced")

    if generic_mode:
        msg = "[Pitch Generator] Generated general-purpose cover letter (3-step chain: analysis → draft → review)."
    else:
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

    # --- XAI: Grounding verification ---
    latest = get_latest_results(state)
    resume_info = latest.get("resume_info") or state.get("resume_info") or {}
    grounding = verify_pitch_grounding(final_pitch, resume_info, best_job or {})
    result["grounding_verification"] = grounding

    # --- XAI: Explainability trace ---
    xai_warnings = list(grounding.get("warnings", []))
    if not valid:
        xai_warnings.extend(issues)
    if generic_mode:
        xai_reasoning = f"Generic cover letter (3-step chain); {len(grounding['verified_claims'])} claims grounded"
        xai_sources = ["match_analysis", "llm_draft", "llm_review"]
    else:
        xai_reasoning = f"4-step chain for {job_title} @ {company}; {len(grounding['verified_claims'])} claims grounded"
        xai_sources = ["company_research", "match_analysis", "llm_draft", "llm_review"]
    result["explainability_trace"] = create_trace(
        agent_name="pitch_generator",
        prompt_version=PITCH_GENERATOR_PROMPT_VERSION,
        confidence=grounding["grounding_score"],
        reasoning=xai_reasoning,
        feature_attributions={"match_analysis": match_analysis},
        grounding_score=grounding["grounding_score"],
        sources_consulted=xai_sources,
        warnings=xai_warnings,
    ).to_dict()

    return result

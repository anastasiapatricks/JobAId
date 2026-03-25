"""Pipeline execution endpoints — run, status, approve, results, step."""

import json
import logging
from typing import List

import threading
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, BackgroundTasks


logger = logging.getLogger("jobaid.api")
from models.api_models import (
    PipelineRunRequest,
    PipelineStatusResponse,
    ApprovalRequest,
    PipelineResultsResponse,
    ResultEntry,
    StepRequest,
    StepResponse,
)
from api.dependencies import get_session, update_session, get_graph
from agents.orchestrator import reset_autonomy, interpret_user_intent
from guardrails.input_filter import validate_chat_message
from utils import get_latest_results
from utils.explainability import ensure_explainability_trace
from graph.nodes import (
    resume_parser_node,
    job_discovery_node,
    market_intelligence_node,
    pitch_generator_node,
    summarizer_node,
)

router = APIRouter(prefix="/api/sessions", tags=["pipeline"])

# Map action names to node functions
_ACTION_NODES = {
    "discovery": job_discovery_node,
    "market_intel": market_intelligence_node,
    "pitching": pitch_generator_node,
    "summarizing": summarizer_node,
}

_STAGE_LABELS = {
    "parsing": "Resume Parsing",
    "discovery": "Job Search",
    "market_intel": "Market Analysis",
    "pitching": "Cover Letter",
    "summarizing": "Final Summary",
}


def _get_completed_stages(state: dict) -> List[str]:
    """Determine which canonical stages have been completed."""
    completed = []
    # Check top-level state or results array
    results = state.get("results", [])
    completed_actions = {r.get("action") for r in results}
    
    for stage in _STAGE_LABELS.keys():
        if stage in completed_actions:
            completed.append(stage)
        elif stage == "parsing" and state.get("resume_info"):
            completed.append(stage)
            
    return completed


def _run_pipeline(session_id: str, state: dict):
    """Run the full pipeline synchronously (called from background task)."""
    try:
        update_session(session_id, status="running")
        reset_autonomy()
        graph = get_graph()
        final_state = graph.invoke(state, config={"recursion_limit": 50})
        update_session(session_id, status="complete", state=final_state, result=final_state)
    except Exception as exc:
        update_session(session_id, status="error", state={"error": str(exc)})


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_single_step(session_id: str, action: str, state: dict):
    """Run a single agent node in a background thread, then set status back to awaiting_input."""
    from utils.llm_logger import set_session_id
    set_session_id(session_id)
    logger.info(json.dumps({"event": "step_start", "session_id": session_id, "action": action}))
    try:
        # Auto-derive job_query from resume when user says "find jobs for my profile"
        # without specifying a role — prevents 0ms no-op in job_discovery
        if action == "discovery" and not state.get("job_query"):
            from utils import get_latest_results
            latest = get_latest_results(state)
            resume_info = (latest.get("resume_debiased") or state.get("resume_debiased")
                           or latest.get("resume_info") or state.get("resume_info") or {})
            exp = resume_info.get("experience", [])
            derived = (resume_info.get("desired_job_title")
                       or resume_info.get("current_title")
                       or (exp[0].get("title") if exp else "")
                       or "")
            if derived:
                state["job_query"] = derived
                logger.info(json.dumps({
                    "event": "job_query_derived",
                    "session_id": session_id,
                    "derived_query": derived,
                }))

        node_fn = _ACTION_NODES.get(action)
        if not node_fn:
            logger.warning(json.dumps({"event": "step_unknown_action", "session_id": session_id, "action": action}))
            update_session(session_id, status="awaiting_input")
            return

        state["last_action"] = action
        state["current_stage"] = action
        update_session(session_id, status="running", state=state)
        result = node_fn(state)

        # Propagate any new messages from the agent into conversation
        # (filter to only messages not already in state to avoid duplication)
        result_msgs = result.get("messages", [])
        if result_msgs:
            existing = state.get("messages") or []
            existing_set = {m.get("content", "") for m in existing}
            new_msgs = [m for m in result_msgs if m.get("content", "") not in existing_set]
            if new_msgs:
                msgs = list(existing)
                msgs.extend(new_msgs)
                state["messages"] = msgs

        # Append result to the results array instead of merging flat
        results_arr = list(state.get("results", []))
        entry = {"action": action, "timestamp": _now_iso()}
        for k, v in result.items():
            if k != "messages":
                entry[k] = v
        results_arr.append(entry)
        state["results"] = results_arr

        # After agent completes, add a follow-up suggestion to conversation
        msgs = list(state.get("messages") or [])
        completed_actions = {r.get("action") for r in results_arr}
        if action == "discovery":
            n_jobs = len(entry.get("scored_jobs", []))
            if n_jobs > 0:
                # Auto-run lightweight skill triage (no LLM, instant)
                from agents.market_intelligence import skill_triage
                triage_result = skill_triage(state)
                entry["skill_triage"] = triage_result.get("skill_triage", [])
                results_arr[-1] = entry
                state["results"] = results_arr

                scored = entry.get("scored_jobs", [])
                quality = entry.get("result_quality", "good")
                original_query = entry.get("original_query", "")
                reformulated = "query_reformulated" in (entry.get("fallback_used") or [])

                if quality == "poor":
                    # Build search suggestions from resume for better next query
                    from utils import get_latest_results as _glr
                    _latest = _glr(state)
                    _ri = (_latest.get("resume_debiased") or state.get("resume_debiased")
                           or _latest.get("resume_info") or state.get("resume_info") or {})
                    _exp = _ri.get("experience", [])
                    _title = (_ri.get("desired_job_title") or _ri.get("current_title")
                              or (_exp[0].get("title") if _exp else "") or "")
                    _skills = (_ri.get("skills") or {})
                    _tech = _skills.get("technical", []) if isinstance(_skills, dict) else []
                    search_chips = []
                    if _title:
                        search_chips.append(f"Find {_title} roles in Singapore")
                    for s in _tech[:3]:
                        search_chips.append(f"Find {s} jobs in Singapore")
                    search_chips.append("Find cybersecurity jobs in Singapore")

                    suggestion = (
                        f"I searched for \"{original_query}\" but the job board didn't return strong matches "
                        f"for that query in Singapore — the results shown are the closest available. "
                        f"Try one of the searches below for better results:"
                    )
                    msgs.append({
                        "role": "assistant",
                        "content": suggestion,
                        "suggestions": search_chips[:5],
                    })
                else:
                    triage = triage_result.get("skill_triage", [])
                    if reformulated:
                        prefix = "I refined the search to better match your profile. "
                    else:
                        prefix = ""

                    if triage:
                        top = triage[0]
                        missing_list = top.get("skills_missing", [])[:3]
                        missing = ", ".join(missing_list) if missing_list else "none identified"
                        suggestion = (
                            f"{prefix}I found {n_jobs} job matches and compared your skills against each role. "
                            f"Your top match is **{top['title']}** at **{top['company']}**"
                            f"{f' (gaps: {missing})' if missing_list else ''}. "
                            "Which role interests you?"
                        )
                    else:
                        suggestion = f"{prefix}I found {n_jobs} job matches! Which one interests you?"

                    # Only show chips for jobs with score > 0
                    job_suggestions = []
                    for j in scored[:5]:
                        if j.get("score", 0) > 0:
                            title = j.get("title", "")
                            company = j.get("company", "")
                            if title and company:
                                job_suggestions.append(f"I'm interested in {title} at {company}")

                    msgs.append({
                        "role": "assistant",
                        "content": suggestion,
                        "suggestions": job_suggestions,
                    })
        elif action == "market_intel":
            selected = state.get("_selected_job") or {}
            title = selected.get("title", "")
            company = selected.get("company", "")
            if title:
                job_label = f"**{title}**" + (f" at **{company}**" if company else "")
                confirm_msg = (
                    f"That's the market research for {job_label}. "
                    f"Would you like me to generate a tailored cover letter for this role?"
                )
                msgs.append({
                    "role": "assistant",
                    "content": confirm_msg,
                    "suggestions": ["Yes, write the cover letter"],
                })
        elif action == "pitching":
            pitch_content = entry.get("final_pitch", "")
            if pitch_content:
                msgs.append({"role": "assistant", "content": (
                    "Your cover letter is ready! Want to pick another role, search for more jobs, or get a session summary?"
                )})
            else:
                # Extract the actual error from the entry for visibility
                entry_errors = entry.get("errors", [])
                if entry_errors:
                    last_err = entry_errors[-1] if isinstance(entry_errors, list) else entry_errors
                    err_detail = last_err.get("error", "") if isinstance(last_err, dict) else str(last_err)
                    entry["pitch_error"] = err_detail
                    logger.error(json.dumps({"event": "pitch_failed", "session_id": session_id, "error": err_detail[:500]}))
                msgs.append({"role": "assistant", "content": (
                    "I wasn't able to generate a cover letter this time. Could you provide more details about the kind of role you're targeting?"
                )})
        state["messages"] = msgs

        update_session(session_id, status="awaiting_input", state=state, result=state)
        logger.info(json.dumps({"event": "step_complete", "session_id": session_id, "action": action}))
    except Exception as exc:
        logger.error(json.dumps({"event": "step_error", "session_id": session_id, "action": action, "error": str(exc)[:500]}))
        errors = list(state.get("errors") or [])
        errors.append({"stage": action, "error": str(exc)})
        state["errors"] = errors
        # Add user-visible error message
        _action_labels = {"discovery": "job search", "market_intel": "market analysis",
                          "pitching": "cover letter generation", "summarizing": "session summary"}
        msgs = list(state.get("messages") or [])
        msgs.append({"role": "assistant", "content":
            f"Sorry, something went wrong during {_action_labels.get(action, action)}. Please try again."})
        state["messages"] = msgs
        update_session(session_id, status="awaiting_input", state=state)


@router.post("/{session_id}/run")
async def run_pipeline(session_id: str, req: PipelineRunRequest, background_tasks: BackgroundTasks):
    logger.info(json.dumps({
        "event": "run_pipeline",
        "session_id": session_id,
        "has_resume": bool(req.resume_text),
        "job_query": (req.job_query or "")[:100],
    }))
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session["status"] == "running":
        raise HTTPException(status_code=409, detail="Pipeline is already running")

    existing_state = session.get("state", {})
    initial_state = {
        "session_id": session_id,
        "messages": existing_state.get("messages", []),
        "current_stage": "intake",
        "stage_history": [],
        "iteration_count": 0,
        "max_iterations": 20,
        "requires_human_approval": False,
        "resume_text": req.resume_text or existing_state.get("resume_text", ""),
        "job_query": req.job_query or existing_state.get("job_query", ""),
        "location_preference": req.location_preference or existing_state.get("location_preference"),
        "decision_log": [],
        "errors": [],
        "fallback_used": [],
        "results": existing_state.get("results", []),
    }

    # Only run resume parsing, then await user input
    update_session(session_id, status="running", state=initial_state)

    def _parse_and_await():
        from utils.llm_logger import set_session_id
        set_session_id(session_id)
        reset_autonomy()  # Fresh LLM call budget for new session
        logger.info(json.dumps({"event": "parse_start", "session_id": session_id}))
        try:
            initial_state["current_stage"] = "parsing"
            update_session(session_id, status="running", state=initial_state)
            result = resume_parser_node(initial_state)
            # Append parse result to the results array
            results_arr = list(initial_state.get("results", []))
            entry = {"action": "parsing", "timestamp": _now_iso()}
            for k, v in result.items():
                if k != "messages":
                    entry[k] = v
            results_arr.append(entry)
            initial_state["results"] = results_arr
            initial_state["last_action"] = "parsing"
            # Also keep resume_info at top level for quick access
            if result.get("resume_info"):
                initial_state["resume_info"] = result["resume_info"]
            if result.get("resume_debiased"):
                initial_state["resume_debiased"] = result["resume_debiased"]
            update_session(session_id, status="awaiting_input", state=initial_state, result=initial_state)
            logger.info(json.dumps({"event": "parse_complete", "session_id": session_id}))
        except Exception as exc:
            logger.error(json.dumps({"event": "parse_error", "session_id": session_id, "error": str(exc)[:500]}))
            update_session(session_id, status="error", state={"error": str(exc)})

    background_tasks.add_task(_parse_and_await)

    return {"session_id": session_id, "status": "started"}


@router.post("/{session_id}/step", response_model=StepResponse)
async def step(session_id: str, req: StepRequest):
    """Conversational step: interpret user message and optionally run an agent."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session["status"] == "running":
        raise HTTPException(status_code=409, detail="An agent is already running")

    state = session.get("state") or session.get("result") or {}

    # Content safety check before any processing
    safe, safety_msg = validate_chat_message(req.message)
    if not safe:
        return StepResponse(
            session_id=session_id,
            status="awaiting_input",
            response_text=safety_msg,
            action="chitchat",
            completed_stages=_get_completed_stages(state)
        )

    # Persist user message to state so the router has conversation history
    msgs = list(state.get("messages") or [])
    msgs.append({"role": "user", "content": req.message})
    state["messages"] = msgs
    logger.info(json.dumps({
        "event": "step_request",
        "session_id": session_id,
        "message": req.message[:200],
    }))

    # Let the orchestrator LLM interpret the user's intent
    intent = interpret_user_intent(req.message, state)
    action = intent.get("action", "chitchat")
    response_text = intent.get("response_text", "")
    logger.info(json.dumps({"event": "step_intent", "session_id": session_id, "action": action}))
    parameters = intent.get("parameters") or {}

    # Persist assistant response to state for future context
    if response_text:
        state["messages"].append({"role": "assistant", "content": response_text})
    update_session(session_id, state=state)

    if action == "chitchat":
        return StepResponse(
            session_id=session_id,
            status="awaiting_input",
            response_text=response_text,
            action=action,
            completed_stages=_get_completed_stages(state)
        )

    # Apply extracted parameters to state
    if parameters.get("job_query"):
        state["job_query"] = parameters["job_query"]
    if parameters.get("location_preference"):
        state["location_preference"] = parameters["location_preference"]

    # For market_intel (job selection) and pitching: reorder scored_jobs so target is at index 0
    if action in ("market_intel", "pitching"):
        target_idx = parameters.get("target_job_index")
        latest = get_latest_results(state)
        scored_jobs = list(latest.get("scored_jobs") or [])
        if scored_jobs and target_idx is not None and isinstance(target_idx, int):
            if 0 <= target_idx < len(scored_jobs):
                target_job = scored_jobs.pop(target_idx)
                scored_jobs.insert(0, target_job)
        # Store reordered scored_jobs at top level so the agent can read it
        if scored_jobs:
            state["scored_jobs"] = scored_jobs
            target = scored_jobs[0]
            state["_selected_job"] = target
            if not state.get("job_query") or state["job_query"] == "":
                state["job_query"] = target.get("title", "")

    # Set running and launch agent in background thread
    state["last_action"] = action
    update_session(session_id, status="running", state=state)
    thread = threading.Thread(target=_run_single_step, args=(session_id, action, state))
    thread.start()

    return StepResponse(
        session_id=session_id,
        status="running",
        response_text=response_text,
        action=action,
        completed_stages=_get_completed_stages(state)
    )


@router.get("/{session_id}/status", response_model=PipelineStatusResponse)
async def get_status(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    state = session.get("state", {})
    return PipelineStatusResponse(
        session_id=session_id,
        status=session["status"],
        current_stage=state.get("current_stage"),
        iteration_count=state.get("iteration_count", 0),
        errors=state.get("errors", []),
    )


@router.post("/{session_id}/approve")
async def approve(session_id: str, req: ApprovalRequest):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    state = session.get("state", {})
    state["requires_human_approval"] = False
    if req.feedback:
        state["human_feedback"] = req.feedback
    update_session(session_id, state=state)

    return {"session_id": session_id, "approved": req.approved}


@router.get("/{session_id}/results", response_model=PipelineResultsResponse)
async def get_results(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    state = session.get("result") or session.get("state", {})
    raw_results = state.get("results", [])

    # Ensure every result entry has explainability_trace
    normalized_entries = []
    for entry in raw_results:
        payload = dict(entry)

        payload = ensure_explainability_trace(
            payload,
            agent_name=payload.get("action", "unknown"),
            prompt_version=payload.get("prompt_version", "demo"),
            confidence=float(payload.get("parsing_confidence", 0.75) or 0.75),
            reasoning=f"{payload.get('action', 'unknown')} completed and returned output.",
            sources_consulted=payload.get("sources_consulted", []),
            warnings=payload.get("warnings", []),
            feature_attributions=payload.get("feature_attributions", {}),
            grounding_score=payload.get("grounding_score"),
        )

        normalized_entries.append(payload)

    # Convert raw dicts to ResultEntry models
    result_entries = []
    for entry in normalized_entries:
        result_entries.append(ResultEntry(**entry))

    return PipelineResultsResponse(
        session_id=session_id,
        status=session["status"],
        last_action=state.get("last_action"),
        resume_info=state.get("resume_info"),
        results=result_entries,
        completed_stages=_get_completed_stages(state),
        selected_job=state.get("_selected_job"),
    )

"""Pipeline execution endpoints — run, status, approve, results, step."""

import threading
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, BackgroundTasks
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
from utils import get_latest_results
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
    try:
        node_fn = _ACTION_NODES.get(action)
        if not node_fn:
            update_session(session_id, status="awaiting_input")
            return

        state["last_action"] = action
        result = node_fn(state)

        # Append result to the results array instead of merging flat
        results_arr = list(state.get("results", []))
        entry = {"action": action, "timestamp": _now_iso()}
        for k, v in result.items():
            if k != "messages":
                entry[k] = v
        results_arr.append(entry)
        state["results"] = results_arr
        update_session(session_id, status="awaiting_input", state=state, result=state)
    except Exception as exc:
        errors = list(state.get("errors") or [])
        errors.append({"stage": action, "error": str(exc)})
        state["errors"] = errors
        update_session(session_id, status="awaiting_input", state=state)


@router.post("/{session_id}/run")
async def run_pipeline(session_id: str, req: PipelineRunRequest, background_tasks: BackgroundTasks):
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
        try:
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
        except Exception as exc:
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

    # Let the orchestrator LLM interpret the user's intent
    intent = interpret_user_intent(req.message, state)
    action = intent.get("action", "chitchat")
    response_text = intent.get("response_text", "")
    parameters = intent.get("parameters") or {}

    if action == "chitchat":
        return StepResponse(
            session_id=session_id,
            status="awaiting_input",
            response_text=response_text,
            action=action,
        )

    # Apply extracted parameters to state
    if parameters.get("job_query"):
        state["job_query"] = parameters["job_query"]
    if parameters.get("location_preference"):
        state["location_preference"] = parameters["location_preference"]

    # For pitching: reorder scored_jobs so target is at index 0
    if action == "pitching":
        target_idx = parameters.get("target_job_index")
        latest = get_latest_results(state)
        scored_jobs = list(latest.get("scored_jobs") or [])
        if scored_jobs and target_idx is not None and isinstance(target_idx, int):
            if 0 <= target_idx < len(scored_jobs):
                target_job = scored_jobs.pop(target_idx)
                scored_jobs.insert(0, target_job)
        # Store reordered scored_jobs at top level so the agent can read it
        state["scored_jobs"] = scored_jobs

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

    # Convert raw dicts to ResultEntry models
    result_entries = []
    for entry in raw_results:
        result_entries.append(ResultEntry(**entry))

    return PipelineResultsResponse(
        session_id=session_id,
        status=session["status"],
        last_action=state.get("last_action"),
        resume_info=state.get("resume_info"),
        results=result_entries,
    )

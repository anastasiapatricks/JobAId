"""Pipeline execution endpoints — run, status, approve, results, step."""

import threading
from fastapi import APIRouter, HTTPException, BackgroundTasks
from models.api_models import (
    PipelineRunRequest,
    PipelineStatusResponse,
    ApprovalRequest,
    PipelineResultsResponse,
    StepRequest,
    StepResponse,
)
from api.dependencies import get_session, update_session, get_graph
from agents.orchestrator import reset_autonomy, interpret_user_intent
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


def _run_single_step(session_id: str, action: str, state: dict):
    """Run a single agent node in a background thread, then set status back to awaiting_input."""
    try:
        node_fn = _ACTION_NODES.get(action)
        if not node_fn:
            update_session(session_id, status="awaiting_input")
            return

        result = node_fn(state)

        # Merge result into existing state
        merged = {**state, **result}
        update_session(session_id, status="awaiting_input", state=merged, result=merged)
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
    }

    # Only run resume parsing, then await user input
    update_session(session_id, status="running", state=initial_state)

    def _parse_and_await():
        try:
            result = resume_parser_node(initial_state)
            merged = {**initial_state, **result}
            update_session(session_id, status="awaiting_input", state=merged, result=merged)
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
        scored_jobs = state.get("scored_jobs") or []
        if scored_jobs and target_idx is not None and isinstance(target_idx, int):
            if 0 <= target_idx < len(scored_jobs):
                target_job = scored_jobs.pop(target_idx)
                scored_jobs.insert(0, target_job)
                state["scored_jobs"] = scored_jobs

    # Set running and launch agent in background thread
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

    return PipelineResultsResponse(
        session_id=session_id,
        status=session["status"],
        resume_info=state.get("resume_info"),
        scored_jobs=state.get("scored_jobs", []),
        skill_gaps=state.get("skill_gaps", []),
        upskilling_roadmap=state.get("upskilling_roadmap", []),
        salary_insights=state.get("salary_insights"),
        industry_trends=state.get("industry_trends", []),
        market_outlook=state.get("market_outlook"),
        final_pitch=state.get("final_pitch"),
        summary=state.get("summary"),
        decision_log=state.get("decision_log", []),
    )

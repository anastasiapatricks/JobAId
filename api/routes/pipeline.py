"""Pipeline execution endpoints — run, status, approve, results."""

import asyncio
import uuid
from fastapi import APIRouter, HTTPException, BackgroundTasks
from models.api_models import (
    PipelineRunRequest,
    PipelineStatusResponse,
    ApprovalRequest,
    PipelineResultsResponse,
)
from api.dependencies import get_session, update_session, get_graph
from agents.orchestrator import reset_autonomy

router = APIRouter(prefix="/api/sessions", tags=["pipeline"])


def _run_pipeline(session_id: str, state: dict):
    """Run the pipeline synchronously (called from background task)."""
    try:
        update_session(session_id, status="running")
        reset_autonomy()
        graph = get_graph()
        final_state = graph.invoke(state, config={"recursion_limit": 50})
        update_session(session_id, status="complete", state=final_state, result=final_state)
    except Exception as exc:
        update_session(session_id, status="error", state={"error": str(exc)})


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

    background_tasks.add_task(_run_pipeline, session_id, initial_state)

    return {"session_id": session_id, "status": "started"}


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
        final_pitch=state.get("final_pitch"),
        summary=state.get("summary"),
        decision_log=state.get("decision_log", []),
    )

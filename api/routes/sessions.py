"""Session management endpoints."""

from fastapi import APIRouter, HTTPException
from models.api_models import SessionCreateRequest, SessionCreateResponse
from api.dependencies import create_session, get_session, delete_session, list_sessions

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=SessionCreateResponse)
async def create(req: SessionCreateRequest):
    initial = {}
    if req.resume_text:
        initial["resume_text"] = req.resume_text
    if req.job_query:
        initial["job_query"] = req.job_query
    if req.location_preference:
        initial["location_preference"] = req.location_preference
    session_id = create_session(initial)
    return SessionCreateResponse(session_id=session_id, status="created")


@router.get("")
async def list_all():
    return list_sessions()


@router.get("/{session_id}")
async def get(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": session["session_id"], "status": session["status"]}


@router.delete("/{session_id}")
async def delete(session_id: str):
    if not delete_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session deleted"}

"""Resume upload endpoint."""

from fastapi import APIRouter, HTTPException, UploadFile, File
from models.api_models import ResumeUploadResponse
from api.dependencies import get_session, update_session

router = APIRouter(prefix="/api/sessions", tags=["resume"])


@router.post("/{session_id}/resume", response_model=ResumeUploadResponse)
async def upload_resume(session_id: str, file: UploadFile = File(...)):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    content = await file.read()
    resume_text = content.decode("utf-8").strip()

    if not resume_text:
        raise HTTPException(status_code=400, detail="Resume file is empty")

    state = session.get("state", {})
    state["resume_text"] = resume_text
    update_session(session_id, state=state)

    return ResumeUploadResponse(
        session_id=session_id,
        resume_text=resume_text,
        message="Resume uploaded successfully",
    )

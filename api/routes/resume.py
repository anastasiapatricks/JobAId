"""Resume upload endpoint."""

import io
import json
import logging

from fastapi import APIRouter, HTTPException, UploadFile, File

logger = logging.getLogger("jobaid.api")
from models.api_models import ResumeUploadResponse
from api.dependencies import get_session, update_session

router = APIRouter(prefix="/api/sessions", tags=["resume"])

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".doc", ".docx"}


def _extract_text(filename: str, content: bytes) -> str:
    """Extract plain text from an uploaded resume file."""
    ext = ""
    if filename:
        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Accepted: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    if ext == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        return text.strip()

    if ext in (".doc", ".docx"):
        from docx import Document

        doc = Document(io.BytesIO(content))
        text = "\n".join(p.text for p in doc.paragraphs)
        return text.strip()

    # .txt — try UTF-8, fall back to latin-1
    try:
        return content.decode("utf-8").strip()
    except UnicodeDecodeError:
        return content.decode("latin-1").strip()


@router.post("/{session_id}/resume", response_model=ResumeUploadResponse)
async def upload_resume(session_id: str, file: UploadFile = File(...)):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    content = await file.read()
    logger.info(json.dumps({
        "event": "resume_upload",
        "session_id": session_id,
        "filename": file.filename or "",
        "file_size": len(content),
    }))

    try:
        resume_text = _extract_text(file.filename, content)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(json.dumps({
            "event": "resume_parse_error",
            "session_id": session_id,
            "error": str(exc)[:500],
        }))
        raise HTTPException(
            status_code=400, detail=f"Could not parse resume: {exc}"
        ) from exc

    if not resume_text:
        raise HTTPException(status_code=400, detail="Resume file is empty")

    logger.info(json.dumps({
        "event": "resume_parsed",
        "session_id": session_id,
        "text_length": len(resume_text),
    }))

    state = session.get("state", {})
    state["resume_text"] = resume_text
    update_session(session_id, state=state)

    return ResumeUploadResponse(
        session_id=session_id,
        resume_text=resume_text,
        message="Resume uploaded successfully",
    )

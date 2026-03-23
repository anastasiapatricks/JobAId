"""FastAPI request/response models."""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class SessionCreateRequest(BaseModel):
    resume_text: Optional[str] = None
    job_query: Optional[str] = None
    location_preference: Optional[str] = None


class SessionCreateResponse(BaseModel):
    session_id: str
    status: str = "created"


class PipelineRunRequest(BaseModel):
    resume_text: str
    job_query: str
    location_preference: Optional[str] = None


class PipelineStatusResponse(BaseModel):
    session_id: str
    status: str
    current_stage: Optional[str] = None
    iteration_count: int = 0
    errors: List[Dict[str, Any]] = Field(default_factory=list)


class ApprovalRequest(BaseModel):
    approved: bool = True
    feedback: Optional[str] = None


class ResultEntry(BaseModel):
    action: str
    timestamp: str

    explainability_trace: Optional[Dict[str, Any]] = None

    scored_jobs: Optional[List[Dict[str, Any]]] = None
    skill_triage: Optional[List[Dict[str, Any]]] = None
    matching_explanation: Optional[List[str]] = None
    job_listings: Optional[List[Dict[str, Any]]] = None
    skill_gaps: Optional[List[Dict[str, Any]]] = None
    upskilling_roadmap: Optional[List[Dict[str, Any]]] = None
    salary_insights: Optional[Dict[str, Any]] = None
    industry_trends: Optional[List[str]] = None
    market_outlook: Optional[str] = None
    draft_pitches: Optional[List[Dict[str, Any]]] = None
    final_pitch: Optional[str] = None
    summary: Optional[str] = None
    resume_info: Optional[Dict[str, Any]] = None
    resume_debiased: Optional[Dict[str, Any]] = None
    parsing_confidence: Optional[float] = None
    missing_fields: Optional[List[str]] = None

    model_config = {"extra": "allow"}


class PipelineResultsResponse(BaseModel):
    session_id: str
    status: str
    last_action: Optional[str] = None
    resume_info: Optional[Dict[str, Any]] = None
    results: List[ResultEntry] = Field(default_factory=list)
    completed_stages: List[str] = Field(default_factory=list)
    selected_job: Optional[Dict[str, Any]] = None
    awaiting_cv_confirmation: bool = False


class StepRequest(BaseModel):
    message: str


class StepResponse(BaseModel):
    session_id: str
    status: str          # "running" | "awaiting_input" | "complete"
    response_text: str   # bot message to display
    action: str          # what orchestrator decided
    completed_stages: List[str] = Field(default_factory=list)


class ResumeUploadResponse(BaseModel):
    session_id: str
    resume_text: str
    message: str = "Resume uploaded successfully"


class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str = "0.2.0"

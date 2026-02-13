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


class PipelineResultsResponse(BaseModel):
    session_id: str
    status: str
    resume_info: Optional[Dict[str, Any]] = None
    scored_jobs: List[Dict[str, Any]] = Field(default_factory=list)
    skill_gaps: List[Dict[str, Any]] = Field(default_factory=list)
    upskilling_roadmap: List[Dict[str, Any]] = Field(default_factory=list)
    salary_insights: Optional[Dict[str, Any]] = None
    industry_trends: List[str] = Field(default_factory=list)
    final_pitch: Optional[str] = None
    summary: Optional[str] = None
    decision_log: List[Dict[str, Any]] = Field(default_factory=list)


class ResumeUploadResponse(BaseModel):
    session_id: str
    resume_text: str
    message: str = "Resume uploaded successfully"


class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str = "0.2.0"

"""JobAId shared state definition for LangGraph."""

from typing import TypedDict, List, Dict, Any, Optional, Literal

OrchestratorStage = Literal[
    "intake",
    "parsing",
    "parsing_review",
    "discovery",
    "discovery_review",
    "market_intel",
    "pitching",
    "pitch_review",
    "summarizing",
    "complete",
    "error",
]


class JobAIdState(TypedDict, total=False):
    # Session
    session_id: str
    messages: List[Dict[str, Any]]

    # FSM orchestrator
    current_stage: OrchestratorStage
    stage_history: List[Dict[str, Any]]
    iteration_count: int
    max_iterations: int
    requires_human_approval: bool
    human_feedback: Optional[str]

    # Input
    resume_text: str
    job_query: str
    location_preference: Optional[str]

    # Resume Parser output
    resume_info: Dict[str, Any]
    resume_debiased: Dict[str, Any]
    parsing_confidence: float
    missing_fields: List[str]

    # Job Discovery output
    job_listings: List[Dict[str, Any]]
    scored_jobs: List[Dict[str, Any]]
    matching_explanation: List[str]

    # Market Intelligence output
    skill_gaps: List[Dict[str, Any]]
    upskilling_roadmap: List[Dict[str, Any]]
    salary_insights: Dict[str, Any]
    industry_trends: List[str]

    # Pitch Generator output
    draft_pitches: List[Dict[str, Any]]
    final_pitch: str

    # Summarizer output
    summary: str
    decision_log: List[Dict[str, Any]]
    errors: List[Dict[str, Any]]
    fallback_used: List[str]

    # Results array — every agent run appends an entry
    results: List[Dict[str, Any]]

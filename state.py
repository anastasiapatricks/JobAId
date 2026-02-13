# state.py — with TypedDict
from typing import TypedDict, List, Dict, Any, Optional

class State(TypedDict, total=False):
    messages: List[Dict[str, Any]]
    volley_msg_left: int
    next_agent: Optional[str]
    stage_idx: int           
    resume_text: str
    job_query: str
    resume_info: Dict[str, Any]
    job_listings: List[Dict[str, Any]]
    scored_jobs: List[Dict[str, Any]]
    final_pitch: str

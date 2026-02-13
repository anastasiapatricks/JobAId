# agents/participant.py
from typing import Dict, Any
from utils import debug

# delegate to the actual step modules
from .resume_parser import resume_parser
from .job_search import job_search
from .relevance_scorer import relevance_scorer_agent
from .pitch_generator import pitch_generator

def participant(agent_name: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the selected pipeline step by delegating to the step modules.
    Always return a next_agent so the coordinator can advance.
    """
    if agent_name == "resume_parser":
        debug("[RESUME] Parsed resume.")
        out = resume_parser(state)
        out["next_agent"] = "job_search"
        return out

    if agent_name == "job_search":
        debug("[JOBS] Fetched job listings.")
        out = job_search(state)
        out["next_agent"] = "relevance_scorer"
        return out

    if agent_name == "relevance_scorer":
        debug("[SCORE] Scored job listings.")
        out = relevance_scorer_agent(state)
        out["next_agent"] = "pitch_generator"
        return out

    if agent_name == "pitch_generator":
        debug("[PITCH] Generated pitch.")
        out = pitch_generator(state)
        out["next_agent"] = None
        return out

    return {
        "messages": [{"role": "assistant", "content": f"(Unknown agent: {agent_name})"}],
        "next_agent": None,
    }

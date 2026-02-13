# agents/coordinator.py
from typing import Dict, Any

PIPELINE = ["resume_parser", "job_search", "relevance_scorer", "pitch_generator"]

def coordinator(state):
    """
    Keep track of the current stage in the pipeline.

    Update state by moving to the next agent in the pipeline by stage_idx.

    Returns: Updated state
    """

    stage_idx = int(state.get("stage_idx", 0))
    print(f"    [DEBUG] [COORDINATOR] stage_idx={stage_idx}")
    if stage_idx < len(PIPELINE):
        next_agent = PIPELINE[stage_idx]
    else:
        next_agent = "human"  # pipeline complete
    print(f"    [DEBUG] [COORDINATOR] Next agent: {next_agent}")
    return {"next_agent": next_agent}

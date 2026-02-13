"""LLM model selection by task type."""

from config.settings import settings


# Task-type → model mapping
_TASK_MODEL_MAP = {
    "resume_parsing": settings.default_model,
    "job_ranking": settings.default_model,
    "market_intelligence": settings.default_model,
    "pitch_draft": settings.default_model,
    "pitch_review": settings.quality_model,  # Higher quality for final review
    "summarization": settings.default_model,
    "confidence_check": settings.default_model,
    "orchestration": settings.default_model,
}


def get_model_for_task(task_type: str) -> str:
    """Return the appropriate model name for a given task type.

    Falls back to default_model if task_type is unknown.
    """
    return _TASK_MODEL_MAP.get(task_type, settings.default_model)

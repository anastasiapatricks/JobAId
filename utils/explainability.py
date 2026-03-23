"""Utility helpers for ensuring result entries carry explainability traces."""

from typing import Any, Dict, List, Optional


def ensure_explainability_trace(
    payload: Dict[str, Any],
    agent_name: str = "unknown",
    prompt_version: str = "demo",
    confidence: float = 0.75,
    reasoning: str = "",
    sources_consulted: Optional[List[str]] = None,
    warnings: Optional[List[str]] = None,
    feature_attributions: Optional[Dict[str, Any]] = None,
    grounding_score: Optional[float] = None,
) -> Dict[str, Any]:
    """Ensure a result entry dict has an explainability_trace field.

    If one already exists it is left untouched.  Otherwise a default trace
    is constructed from the supplied keyword arguments and written in-place.
    """
    if payload.get("explainability_trace"):
        return payload

    trace = {
        "agent_name": agent_name,
        "prompt_version": prompt_version,
        "confidence": confidence,
        "reasoning": reasoning or f"{agent_name} completed and returned output.",
        "feature_attributions": feature_attributions or {},
        "grounding_score": grounding_score if grounding_score is not None else confidence,
        "sources_consulted": sources_consulted or [],
        "warnings": warnings or [],
    }

    payload["explainability_trace"] = trace
    return payload

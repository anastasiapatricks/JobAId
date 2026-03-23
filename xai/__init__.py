"""Explainable AI (XAI) module — unified tracing, SHAP/LIME explanations, fairness, grounding."""

from xai.trace import ExplainabilityTrace, create_trace
from xai.explainers import shap_skill_attribution, lime_job_explanation
from xai.fairness import statistical_parity_check, equal_opportunity_check
from xai.grounding import verify_pitch_grounding

__all__ = [
    "ExplainabilityTrace",
    "create_trace",
    "shap_skill_attribution",
    "lime_job_explanation",
    "statistical_parity_check",
    "equal_opportunity_check",
    "verify_pitch_grounding",
]

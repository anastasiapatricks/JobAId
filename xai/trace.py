"""Unified explainability trace dataclass for all agents."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class ExplainabilityTrace:
    """Captures explainability metadata for a single agent invocation."""

    agent_name: str
    prompt_version: str
    confidence: float = 0.0
    reasoning: str = ""
    feature_attributions: Dict[str, Any] = field(default_factory=dict)
    grounding_score: float = 0.0
    sources_consulted: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "prompt_version": self.prompt_version,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "feature_attributions": self.feature_attributions,
            "grounding_score": self.grounding_score,
            "sources_consulted": self.sources_consulted,
            "warnings": self.warnings,
            "timestamp": self.timestamp,
        }


def create_trace(
    agent_name: str,
    prompt_version: str,
    confidence: float = 0.0,
    reasoning: str = "",
    feature_attributions: Optional[Dict[str, Any]] = None,
    grounding_score: float = 0.0,
    sources_consulted: Optional[List[str]] = None,
    warnings: Optional[List[str]] = None,
) -> ExplainabilityTrace:
    """Factory for creating an ExplainabilityTrace with defaults."""
    return ExplainabilityTrace(
        agent_name=agent_name,
        prompt_version=prompt_version,
        confidence=confidence,
        reasoning=reasoning,
        feature_attributions=feature_attributions or {},
        grounding_score=grounding_score,
        sources_consulted=sources_consulted or [],
        warnings=warnings or [],
    )

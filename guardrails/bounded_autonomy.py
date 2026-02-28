"""Bounded autonomy enforcement — prevents runaway agent loops."""

from typing import Dict, Any, List
from config.settings import settings


class BoundedAutonomy:
    """Tracks iteration counts and enforces limits per session."""

    def __init__(
        self,
        max_iterations: int = settings.max_iterations,
        max_retries_per_stage: int = settings.max_retries_per_stage,
        max_llm_calls: int = settings.max_llm_calls,
    ):
        self.max_iterations = max_iterations
        self.max_retries_per_stage = max_retries_per_stage
        self.max_llm_calls = max_llm_calls
        self._stage_retries: Dict[str, int] = {}
        self._llm_call_count = 0

    def check_iteration_limit(self, iteration_count: int) -> bool:
        """Return True if within limits, False if exceeded."""
        return iteration_count < self.max_iterations

    def record_stage_retry(self, stage: str) -> bool:
        """Record a retry for a stage. Return True if retry is allowed."""
        self._stage_retries[stage] = self._stage_retries.get(stage, 0) + 1
        return self._stage_retries[stage] <= self.max_retries_per_stage

    def get_stage_retries(self, stage: str) -> int:
        return self._stage_retries.get(stage, 0)

    def record_llm_call(self) -> bool:
        """Record an LLM call. Return True if within limits."""
        self._llm_call_count += 1
        return self._llm_call_count <= self.max_llm_calls

    def get_llm_call_count(self) -> int:
        return self._llm_call_count

    def reset(self):
        self._stage_retries.clear()
        self._llm_call_count = 0

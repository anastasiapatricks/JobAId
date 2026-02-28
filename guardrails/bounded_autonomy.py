"""Bounded autonomy enforcement — prevents runaway agent loops."""

import json
import logging
from typing import Dict, Any, List
from datetime import datetime, timezone
from config.settings import settings

_guard_logger = logging.getLogger("jobaid.guardrails")


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
        within = iteration_count < self.max_iterations
        if not within:
            _guard_logger.warning(json.dumps({
                "event": "guardrail_triggered",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "guardrail": "iteration_limit",
                "stage": "orchestrator",
                "detail": f"iteration {iteration_count} >= max {self.max_iterations}",
            }))
        return within

    def record_stage_retry(self, stage: str) -> bool:
        """Record a retry for a stage. Return True if retry is allowed."""
        self._stage_retries[stage] = self._stage_retries.get(stage, 0) + 1
        allowed = self._stage_retries[stage] <= self.max_retries_per_stage
        if not allowed:
            _guard_logger.warning(json.dumps({
                "event": "guardrail_triggered",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "guardrail": "stage_retry_limit",
                "stage": stage,
                "detail": f"retries {self._stage_retries[stage]} > max {self.max_retries_per_stage}",
            }))
        return allowed

    def get_stage_retries(self, stage: str) -> int:
        return self._stage_retries.get(stage, 0)

    def record_llm_call(self) -> bool:
        """Record an LLM call. Return True if within limits."""
        self._llm_call_count += 1
        within = self._llm_call_count <= self.max_llm_calls
        if not within:
            _guard_logger.warning(json.dumps({
                "event": "guardrail_triggered",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "guardrail": "llm_call_limit",
                "stage": "global",
                "detail": f"llm calls {self._llm_call_count} > max {self.max_llm_calls}",
            }))
        return within

    def get_llm_call_count(self) -> int:
        return self._llm_call_count

    def reset(self):
        self._stage_retries.clear()
        self._llm_call_count = 0

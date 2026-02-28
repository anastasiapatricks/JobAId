"""Bounded autonomy enforcement tests."""

import pytest
from guardrails.bounded_autonomy import BoundedAutonomy


class TestIterationLimit:
    """Test iteration count enforcement."""

    def test_within_limit(self):
        ba = BoundedAutonomy(max_iterations=20)
        assert ba.check_iteration_limit(0)
        assert ba.check_iteration_limit(10)
        assert ba.check_iteration_limit(19)

    def test_at_limit(self):
        ba = BoundedAutonomy(max_iterations=20)
        assert not ba.check_iteration_limit(20)

    def test_exceeds_limit(self):
        ba = BoundedAutonomy(max_iterations=20)
        assert not ba.check_iteration_limit(25)

    def test_custom_limit(self):
        ba = BoundedAutonomy(max_iterations=5)
        assert ba.check_iteration_limit(4)
        assert not ba.check_iteration_limit(5)


class TestStageRetryLimit:
    """Test per-stage retry enforcement."""

    def test_first_retry_allowed(self):
        ba = BoundedAutonomy(max_retries_per_stage=2)
        assert ba.record_stage_retry("parse_resume")

    def test_second_retry_allowed(self):
        ba = BoundedAutonomy(max_retries_per_stage=2)
        ba.record_stage_retry("parse_resume")
        assert ba.record_stage_retry("parse_resume")

    def test_third_retry_blocked(self):
        ba = BoundedAutonomy(max_retries_per_stage=2)
        ba.record_stage_retry("parse_resume")
        ba.record_stage_retry("parse_resume")
        assert not ba.record_stage_retry("parse_resume")

    def test_separate_stages_tracked_independently(self):
        ba = BoundedAutonomy(max_retries_per_stage=1)
        ba.record_stage_retry("stage_a")
        assert ba.record_stage_retry("stage_b")

    def test_get_stage_retries(self):
        ba = BoundedAutonomy()
        assert ba.get_stage_retries("unknown") == 0
        ba.record_stage_retry("stage_a")
        assert ba.get_stage_retries("stage_a") == 1


class TestLLMCallLimit:
    """Test LLM call count enforcement."""

    def test_within_limit(self):
        ba = BoundedAutonomy(max_llm_calls=50)
        for _ in range(50):
            assert ba.record_llm_call()

    def test_exceeds_limit(self):
        ba = BoundedAutonomy(max_llm_calls=3)
        ba.record_llm_call()
        ba.record_llm_call()
        ba.record_llm_call()
        assert not ba.record_llm_call()

    def test_get_llm_call_count(self):
        ba = BoundedAutonomy()
        assert ba.get_llm_call_count() == 0
        ba.record_llm_call()
        ba.record_llm_call()
        assert ba.get_llm_call_count() == 2


class TestReset:
    """Test reset clears all counters."""

    def test_reset_clears_retries(self):
        ba = BoundedAutonomy(max_retries_per_stage=1)
        ba.record_stage_retry("stage_a")
        ba.record_stage_retry("stage_a")
        ba.reset()
        assert ba.get_stage_retries("stage_a") == 0
        assert ba.record_stage_retry("stage_a")

    def test_reset_clears_llm_calls(self):
        ba = BoundedAutonomy(max_llm_calls=2)
        ba.record_llm_call()
        ba.record_llm_call()
        ba.reset()
        assert ba.get_llm_call_count() == 0
        assert ba.record_llm_call()

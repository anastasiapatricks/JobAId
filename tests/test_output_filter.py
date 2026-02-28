"""Output validation and grounding check tests."""

import pytest
from guardrails.output_filter import (
    validate_resume_output,
    validate_job_discovery_output,
    validate_pitch_output,
    check_grounding,
)


class TestValidateResumeOutput:
    """Test resume parser output validation."""

    def test_valid_resume_output(self, sample_resume_info):
        valid, issues = validate_resume_output({"resume_info": sample_resume_info})
        assert valid
        assert issues == []

    def test_empty_resume_info(self):
        valid, issues = validate_resume_output({"resume_info": {}})
        assert not valid
        assert any("empty" in i for i in issues)

    def test_missing_resume_info(self):
        valid, issues = validate_resume_output({})
        assert not valid

    def test_resume_info_wrong_type(self):
        valid, issues = validate_resume_output({"resume_info": "not a dict"})
        assert not valid
        assert any("not a dict" in i for i in issues)


class TestValidateJobDiscoveryOutput:
    """Test job discovery output validation."""

    def test_valid_job_output(self):
        result = {
            "scored_jobs": [
                {"title": "Engineer", "score": 0.9, "company": "Acme"},
                {"title": "Developer", "score": 0.8, "company": "Corp"},
            ]
        }
        valid, issues = validate_job_discovery_output(result)
        assert valid
        assert issues == []

    def test_scored_jobs_not_list(self):
        valid, issues = validate_job_discovery_output({"scored_jobs": "invalid"})
        assert not valid
        assert any("not a list" in i for i in issues)

    def test_job_missing_score(self):
        result = {"scored_jobs": [{"title": "Engineer"}]}
        valid, issues = validate_job_discovery_output(result)
        assert not valid
        assert any("missing 'score'" in i for i in issues)

    def test_job_missing_title(self):
        result = {"scored_jobs": [{"score": 0.9}]}
        valid, issues = validate_job_discovery_output(result)
        assert not valid
        assert any("missing 'title'" in i for i in issues)

    def test_job_not_dict(self):
        result = {"scored_jobs": ["not a dict"]}
        valid, issues = validate_job_discovery_output(result)
        assert not valid

    def test_empty_scored_jobs(self):
        valid, issues = validate_job_discovery_output({"scored_jobs": []})
        assert valid


class TestValidatePitchOutput:
    """Test pitch generator output validation."""

    def test_valid_pitch(self):
        pitch = "Dear Hiring Manager, I am writing to express my strong interest in the position. " * 3
        valid, issues = validate_pitch_output({"final_pitch": pitch})
        assert valid
        assert issues == []

    def test_empty_pitch(self):
        valid, issues = validate_pitch_output({"final_pitch": ""})
        assert not valid
        assert any("empty" in i for i in issues)

    def test_missing_pitch(self):
        valid, issues = validate_pitch_output({})
        assert not valid

    def test_short_pitch(self):
        valid, issues = validate_pitch_output({"final_pitch": "Hi."})
        assert not valid
        assert any("short" in i for i in issues)


class TestCheckGrounding:
    """Test grounding score calculation."""

    def test_fully_grounded(self, sample_state):
        summary = "John Doe should apply to Google. Key skill gap: Terraform."
        score = check_grounding(summary, sample_state)
        assert score == 1.0

    def test_partially_grounded(self, sample_state):
        summary = "John Doe has strong qualifications for various roles."
        score = check_grounding(summary, sample_state)
        assert 0.0 < score < 1.0

    def test_ungrounded(self, sample_state):
        summary = "This is a generic summary with no specific references."
        score = check_grounding(summary, sample_state)
        assert score == 0.0

    def test_empty_summary(self, sample_state):
        score = check_grounding("", sample_state)
        assert score == 0.0

    def test_empty_state(self):
        score = check_grounding("Some summary text", {})
        assert score == 1.0  # Nothing to check

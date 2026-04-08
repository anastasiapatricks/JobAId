"""Output validation and grounding check tests."""

import pytest
from guardrails.output_filter import (
    validate_resume_output,
    validate_job_discovery_output,
    validate_pitch_output,
    check_grounding,
    check_pitch_pii_leakage,
    check_pitch_professionalism,
    check_pitch_grounding,
    check_pitch_fabrication,
    MAX_PITCH_LENGTH,
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
        summary = "The candidate should apply to Google for various roles."
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


class TestValidatePitchMaxLength:
    """Test pitch max length guardrail."""

    def test_pitch_exceeds_max_length(self):
        long_pitch = "A" * (MAX_PITCH_LENGTH + 1)
        valid, issues = validate_pitch_output({"final_pitch": long_pitch})
        assert not valid
        assert any("max length" in i for i in issues)

    def test_pitch_within_max_length(self):
        pitch = "Dear Hiring Manager, I am writing to express my interest. " * 10
        valid, issues = validate_pitch_output({"final_pitch": pitch})
        assert valid


class TestCheckPitchPiiLeakage:
    """Test PII leakage detection in generated pitch."""

    def test_clean_pitch(self):
        pitch = "I am excited to apply for this role at Google. My experience in Python makes me a strong fit."
        ok, issues = check_pitch_pii_leakage(pitch)
        assert ok
        assert issues == []

    def test_email_leakage(self):
        pitch = "Please contact me at john.doe@example.com for further discussion."
        ok, issues = check_pitch_pii_leakage(pitch)
        assert not ok
        assert any("email" in i for i in issues)

    def test_phone_leakage(self):
        pitch = "You can reach me at +65 9123 4567 any time."
        ok, issues = check_pitch_pii_leakage(pitch)
        assert not ok
        assert any("phone" in i for i in issues)

    def test_both_pii_types(self):
        pitch = "Email: test@corp.com, Phone: 91234567."
        ok, issues = check_pitch_pii_leakage(pitch)
        assert not ok
        assert len(issues) == 2


class TestCheckPitchProfessionalism:
    """Test professionalism check on generated pitch."""

    def test_professional_pitch(self):
        pitch = "I am eager to bring my expertise in cloud computing to your team at Amazon Web Services."
        ok, issues = check_pitch_professionalism(pitch)
        assert ok
        assert issues == []

    def test_offensive_language(self):
        pitch = "This damn job is exactly what I need, no bullshit."
        ok, issues = check_pitch_professionalism(pitch)
        assert not ok
        assert any("unprofessional" in i for i in issues)

    def test_informal_internet_slang(self):
        pitch = "lol I would be a great fit for this role omg."
        ok, issues = check_pitch_professionalism(pitch)
        assert not ok
        assert any("unprofessional" in i for i in issues)


class TestCheckPitchGrounding:
    """Test that pitch references actual candidate skills."""

    def test_well_grounded_pitch(self):
        pitch = "My experience with Python, AWS, and Docker has prepared me well for this role."
        skills = ["Python", "AWS", "Docker", "Kubernetes"]
        score, warnings = check_pitch_grounding(pitch, skills)
        assert score >= 0.5
        assert warnings == []

    def test_poorly_grounded_pitch(self):
        pitch = "I am a great candidate who would love to work at your company."
        skills = ["Python", "AWS", "Docker", "Kubernetes", "React"]
        score, warnings = check_pitch_grounding(pitch, skills)
        assert score < 0.3
        assert any("fabricated" in w for w in warnings)

    def test_no_skills_to_check(self):
        pitch = "Generic cover letter content here."
        score, warnings = check_pitch_grounding(pitch, [])
        assert score == 1.0
        assert warnings == []

    def test_partial_grounding(self):
        pitch = "My Python expertise and Docker knowledge make me an ideal candidate."
        skills = ["Python", "Docker", "AWS", "Kubernetes", "Java", "React"]
        score, warnings = check_pitch_grounding(pitch, skills)
        assert 0.3 <= score < 1.0


class TestCheckPitchFabrication:
    """Test fabrication/hallucination detection in pitch."""

    def test_clean_pitch(self):
        pitch = "I am excited to apply for the Software Engineer role at Google."
        ok, issues = check_pitch_fabrication(pitch)
        assert ok
        assert issues == []

    def test_placeholder_your_name(self):
        pitch = "Dear Hiring Manager, [Your Name] is writing to apply."
        ok, issues = check_pitch_fabrication(pitch)
        assert not ok
        assert any("placeholder" in i for i in issues)

    def test_placeholder_insert(self):
        pitch = "I have [insert number] years of experience in the field."
        ok, issues = check_pitch_fabrication(pitch)
        assert not ok
        assert any("placeholder" in i for i in issues)

    def test_placeholder_hiring_manager(self):
        pitch = "Dear [Hiring Manager], I am writing to express my interest."
        ok, issues = check_pitch_fabrication(pitch)
        assert not ok

    def test_placeholder_company_name(self):
        pitch = "I am thrilled to apply to [Company Name] for the role."
        ok, issues = check_pitch_fabrication(pitch)
        assert not ok

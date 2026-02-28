"""PII sanitization and de-biasing tests."""

import pytest
from tools.pii_sanitizer import strip_pii, sanitize_text


class TestStripPII:
    """Test PII removal from resume info dict."""

    def test_removes_name(self, sample_resume_info):
        result = strip_pii(sample_resume_info)
        assert "name" not in result.get("contact_info", {})

    def test_removes_email(self, sample_resume_info):
        result = strip_pii(sample_resume_info)
        assert "email" not in result.get("contact_info", {})

    def test_removes_phone(self, sample_resume_info):
        result = strip_pii(sample_resume_info)
        assert "phone" not in result.get("contact_info", {})

    def test_preserves_skills(self, sample_resume_info):
        result = strip_pii(sample_resume_info)
        assert result["skills"] == sample_resume_info["skills"]

    def test_preserves_experience(self, sample_resume_info):
        result = strip_pii(sample_resume_info)
        assert result["experience"] == sample_resume_info["experience"]

    def test_preserves_education(self, sample_resume_info):
        result = strip_pii(sample_resume_info)
        assert result["education"] == sample_resume_info["education"]

    def test_does_not_mutate_original(self, sample_resume_info):
        original_name = sample_resume_info["contact_info"]["name"]
        strip_pii(sample_resume_info)
        assert sample_resume_info["contact_info"]["name"] == original_name


class TestGenderIndicatorRemoval:
    """Test gender indicator removal from professional summary."""

    def test_removes_he_pronoun(self):
        info = {"professional_summary": "He is an experienced engineer."}
        result = strip_pii(info)
        assert "He" not in result["professional_summary"].split()

    def test_removes_she_pronoun(self):
        info = {"professional_summary": "She leads a team of developers."}
        result = strip_pii(info)
        assert "She" not in result["professional_summary"].split()

    def test_removes_mr_title(self):
        info = {"professional_summary": "Mr. Smith is a project manager."}
        result = strip_pii(info)
        words = result["professional_summary"].split()
        assert not any(w.lower().strip(".,") == "mr" for w in words)

    def test_preserves_non_gendered_content(self):
        info = {"professional_summary": "Experienced software engineer with Python skills."}
        result = strip_pii(info)
        assert "software" in result["professional_summary"]
        assert "Python" in result["professional_summary"]


class TestSanitizeText:
    """Test raw text sanitization."""

    def test_redacts_email(self):
        text = "Contact me at john@example.com for details."
        result = sanitize_text(text)
        assert "john@example.com" not in result
        assert "[EMAIL]" in result

    def test_redacts_phone(self):
        text = "Call me at +65 9123 4567."
        result = sanitize_text(text)
        assert "9123 4567" not in result
        assert "[PHONE]" in result

    def test_preserves_normal_text(self):
        text = "Experienced in Python and Java development."
        result = sanitize_text(text)
        assert result == text

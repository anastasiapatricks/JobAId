"""Skill Triage tests — the lightweight, no-LLM skill gap snapshot.

Covers:
- Basic skill matching (intersection/difference)
- Case insensitivity
- Edge cases: empty jobs, no skills, perfect match
- No LLM calls (pure Python)
- Message format
- Top-N limiting
"""

import sys
from unittest.mock import patch, MagicMock

import pytest

import agents.market_intelligence as _mi_mod
_MI_MOD = sys.modules["agents.market_intelligence"]

from agents.market_intelligence import skill_triage


@pytest.fixture
def triage_state():
    """State with parsed resume and scored jobs for triage testing."""
    return {
        "resume_debiased": {
            "skills": {
                "technical": ["Python", "IDA Pro", "x64dbg", "YARA"],
                "soft": ["Leadership"],
                "certifications": ["GREM"],
            },
        },
        "scored_jobs": [
            {
                "title": "Malware Analyst",
                "company": "CrowdStrike",
                "score": 92,
                "keywords": ["python", "ida pro", "yara", "ghidra", "c"],
            },
            {
                "title": "Threat Intel Analyst",
                "company": "Mandiant",
                "score": 85,
                "keywords": ["python", "yara", "mitre att&ck", "threat intelligence"],
            },
            {
                "title": "Backend Engineer",
                "company": "Google",
                "score": 60,
                "keywords": ["python", "go", "kubernetes", "docker"],
            },
        ],
        "results": [],
    }


class TestSkillTriage:
    """Unit tests for the skill_triage() function."""

    def test_basic_triage(self, triage_state):
        result = skill_triage(triage_state)
        triage = result["skill_triage"]
        assert len(triage) == 3

        top = triage[0]
        assert top["title"] == "Malware Analyst"
        assert top["company"] == "CrowdStrike"
        assert "python" in top["skills_matched"]
        assert "ida pro" in top["skills_matched"]
        assert "yara" in top["skills_matched"]
        assert "ghidra" in top["skills_missing"]
        assert "c" in top["skills_missing"]

    def test_match_ratio(self, triage_state):
        result = skill_triage(triage_state)
        top = result["skill_triage"][0]
        # 3 matched (python, ida pro, yara) out of 5 keywords
        assert top["match_ratio"] == 0.6

    def test_case_insensitive(self):
        state = {
            "resume_debiased": {
                "skills": {"technical": ["PYTHON", "Docker"], "soft": [], "certifications": []},
            },
            "scored_jobs": [
                {"title": "Dev", "company": "X", "score": 90, "keywords": ["python", "docker"]},
            ],
            "results": [],
        }
        result = skill_triage(state)
        top = result["skill_triage"][0]
        assert "python" in top["skills_matched"]
        assert "docker" in top["skills_matched"]
        assert top["skills_missing"] == []
        assert top["match_ratio"] == 1.0

    def test_empty_scored_jobs(self):
        state = {
            "resume_debiased": {"skills": {"technical": ["Python"], "soft": [], "certifications": []}},
            "scored_jobs": [],
            "results": [],
        }
        result = skill_triage(state)
        assert result["skill_triage"] == []

    def test_no_resume_skills(self):
        state = {
            "scored_jobs": [
                {"title": "Dev", "company": "X", "score": 90, "keywords": ["python", "go"]},
            ],
            "results": [],
        }
        result = skill_triage(state)
        top = result["skill_triage"][0]
        assert top["skills_matched"] == []
        assert sorted(top["skills_missing"]) == ["go", "python"]
        assert top["match_ratio"] == 0.0

    def test_perfect_match(self):
        state = {
            "resume_debiased": {
                "skills": {"technical": ["Python", "Go", "Docker"], "soft": [], "certifications": []},
            },
            "scored_jobs": [
                {"title": "Dev", "company": "X", "score": 90, "keywords": ["python", "go", "docker"]},
            ],
            "results": [],
        }
        result = skill_triage(state)
        top = result["skill_triage"][0]
        assert top["skills_missing"] == []
        assert top["match_ratio"] == 1.0

    def test_top_n_limit(self):
        """Only processes top 10 scored jobs."""
        state = {
            "resume_debiased": {"skills": {"technical": ["Python"], "soft": [], "certifications": []}},
            "scored_jobs": [
                {"title": f"Job {i}", "company": "X", "score": 90 - i, "keywords": ["python"]}
                for i in range(20)
            ],
            "results": [],
        }
        result = skill_triage(state)
        assert len(result["skill_triage"]) == 10

    def test_no_llm_calls(self, triage_state):
        """Verify the triage function makes zero LLM calls."""
        with patch.object(_MI_MOD, "ChatOpenAI") as mock_llm, \
             patch.object(_MI_MOD, "logged_invoke") as mock_invoke:
            skill_triage(triage_state)
            assert not mock_llm.called
            assert not mock_invoke.called

    def test_message_format(self, triage_state):
        result = skill_triage(triage_state)
        msg = result["messages"][0]["content"]
        assert msg.startswith("[Skill Triage]")
        assert "CrowdStrike" in msg
        assert "Malware Analyst" in msg

    def test_message_for_empty_jobs(self):
        state = {"scored_jobs": [], "results": []}
        result = skill_triage(state)
        assert "No scored jobs" in result["messages"][0]["content"]

    def test_handles_missing_keywords(self):
        state = {
            "resume_debiased": {"skills": {"technical": ["Python"], "soft": [], "certifications": []}},
            "scored_jobs": [
                {"title": "Dev", "company": "X", "score": 90},  # no keywords field
            ],
            "results": [],
        }
        result = skill_triage(state)
        top = result["skill_triage"][0]
        assert top["skills_matched"] == []
        assert top["skills_missing"] == []
        assert top["match_ratio"] == 0.0

    def test_skills_from_results_array(self):
        """Skills can come from the results array (debiased resume entry)."""
        state = {
            "results": [
                {
                    "action": "parsing",
                    "resume_debiased": {
                        "skills": {"technical": ["Rust", "C"], "soft": [], "certifications": []},
                    },
                },
            ],
            "scored_jobs": [
                {"title": "Dev", "company": "X", "score": 90, "keywords": ["rust", "go"]},
            ],
        }
        result = skill_triage(state)
        assert "rust" in result["skill_triage"][0]["skills_matched"]
        assert "go" in result["skill_triage"][0]["skills_missing"]

    def test_duplicate_skills_handled(self):
        """Duplicate skills in resume or keywords don't cause issues."""
        state = {
            "resume_debiased": {
                "skills": {"technical": ["Python", "Python"], "soft": [], "certifications": []},
            },
            "scored_jobs": [
                {"title": "Dev", "company": "X", "score": 90, "keywords": ["python", "python", "go"]},
            ],
            "results": [],
        }
        result = skill_triage(state)
        top = result["skill_triage"][0]
        assert top["skills_matched"] == ["python"]
        assert top["skills_missing"] == ["go"]

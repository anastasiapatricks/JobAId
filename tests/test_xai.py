"""Tests for the XAI module — traces, SHAP, LIME, fairness, grounding."""

import pytest
from xai.trace import ExplainabilityTrace, create_trace
from xai.explainers import shap_skill_attribution, lime_job_explanation
from xai.fairness import statistical_parity_check, equal_opportunity_check
from xai.grounding import verify_pitch_grounding


# ── ExplainabilityTrace ──────────────────────────────────────────────


class TestExplainabilityTrace:
    def test_create_trace_defaults(self):
        trace = create_trace(agent_name="test", prompt_version="1.0.0")
        assert trace.agent_name == "test"
        assert trace.confidence == 0.0
        assert trace.feature_attributions == {}
        assert trace.warnings == []
        assert trace.timestamp  # non-empty

    def test_create_trace_with_values(self):
        trace = create_trace(
            agent_name="parser",
            prompt_version="1.0.0",
            confidence=0.85,
            reasoning="parsed ok",
            feature_attributions={"skills": 1.0},
            warnings=["low confidence"],
        )
        assert trace.confidence == 0.85
        assert trace.feature_attributions == {"skills": 1.0}

    def test_to_dict_serialization(self):
        trace = create_trace(agent_name="test", prompt_version="2.0.0", confidence=0.5)
        d = trace.to_dict()
        assert isinstance(d, dict)
        assert d["agent_name"] == "test"
        assert d["prompt_version"] == "2.0.0"
        assert d["confidence"] == 0.5
        assert "timestamp" in d

    def test_dataclass_fields(self):
        trace = ExplainabilityTrace(
            agent_name="a", prompt_version="1.0",
            sources_consulted=["llm", "rag"],
        )
        assert trace.sources_consulted == ["llm", "rag"]
        assert trace.grounding_score == 0.0


# ── SHAP Attribution ─────────────────────────────────────────────────


class TestShapAttribution:
    def test_balanced_skills(self):
        result = shap_skill_attribution(
            ["python", "java", "sql"],
            ["python", "java", "sql", "docker"],
        )
        assert isinstance(result, dict)
        # Skills that match job keywords should have positive Shapley values
        assert result.get("python", 0) > 0
        assert result.get("java", 0) > 0
        # Meta shows keyword method
        assert result["_meta"]["method"] == "keywords"
        assert result["_meta"]["overlap_count"] == 3

    def test_empty_skills(self):
        result = shap_skill_attribution([], ["python", "java"])
        assert result == {}

    def test_empty_keywords(self):
        result = shap_skill_attribution(["python"], [])
        assert result == {}

    def test_single_skill(self):
        result = shap_skill_attribution(["python"], ["python", "java"])
        assert "python" in result
        assert result["python"] > 0

    def test_description_fallback_when_no_keyword_overlap(self):
        """When keywords don't overlap but description mentions candidate skills,
        SHAP should enrich from description and produce non-zero values."""
        result = shap_skill_attribution(
            candidate_skills=["python", "docker", "kubernetes"],
            job_keywords=["java", "spring boot"],  # no overlap
            job_description="We need someone with python and docker experience",
        )
        assert result.get("python", 0) > 0 or result.get("docker", 0) > 0
        assert result["_meta"]["method"] == "keywords+description"


# ── LIME Explanation ─────────────────────────────────────────────────


class TestLimeExplanation:
    def test_top_impact_skills(self):
        result = lime_job_explanation(
            ["python", "java", "sql", "docker"],
            ["python", "java", "sql", "kubernetes"],
            top_n=3,
        )
        assert len(result) <= 3
        assert all("skill" in r and "impact" in r for r in result)
        # Skills that overlap with job keywords should have positive impact
        matching = [r for r in result if r["impact"] > 0]
        assert len(matching) > 0

    def test_no_overlap(self):
        result = lime_job_explanation(
            ["python", "java"],
            ["kubernetes", "docker"],
            top_n=5,
        )
        # No skill matches keywords, so removing any skill has zero impact
        for r in result:
            if "_meta" in r:
                continue
            assert r["impact"] == 0

    def test_full_overlap(self):
        result = lime_job_explanation(
            ["python", "java"],
            ["python", "java"],
            top_n=5,
        )
        # Each skill matters — removing either drops the score
        for r in result:
            if "_meta" in r:
                continue
            assert r["impact"] > 0
            assert r["direction"] == "positive"

    def test_description_fallback_when_no_keyword_overlap(self):
        """When keywords don't overlap, LIME enriches from description."""
        result = lime_job_explanation(
            candidate_skills=["python", "docker"],
            job_keywords=["java", "spring boot"],  # no overlap
            top_n=3,
            job_description="Looking for python and docker skills",
        )
        impacts = [r for r in result if "impact" in r and r.get("impact", 0) > 0]
        assert len(impacts) > 0
        assert result[0].get("_meta", {}).get("method") == "keywords+description"


# ── Fairness Audit ───────────────────────────────────────────────────


class TestFairnessAudit:
    def _make_jobs(self, scores_locations):
        return [{"score": s, "location": loc} for s, loc in scores_locations]

    def test_balanced_scoring(self):
        jobs = self._make_jobs([
            (80, "Singapore"), (75, "Singapore"),
            (78, "Remote"), (73, "Remote"),
        ])
        result = statistical_parity_check(jobs, "Singapore")
        assert result["passed"] is True
        assert result["gap"] <= 10

    def test_biased_scoring(self):
        jobs = self._make_jobs([
            (90, "Singapore"), (85, "Singapore"),
            (50, "Remote"), (45, "Remote"),
        ])
        result = statistical_parity_check(jobs, "Singapore")
        assert result["passed"] is False
        assert result["gap"] > 10

    def test_empty_jobs(self):
        result = statistical_parity_check([], "Singapore")
        assert result["passed"] is True

    def test_no_location(self):
        jobs = self._make_jobs([(80, "Singapore"), (75, "Remote")])
        result = statistical_parity_check(jobs, "")
        assert result["passed"] is True
        assert "Insufficient data" in result["detail"]

    def test_equal_opportunity_balanced(self):
        jobs = self._make_jobs([
            (80, "Singapore"), (60, "Singapore"),
            (75, "Remote"), (55, "Remote"),
        ])
        result = equal_opportunity_check(jobs, "Singapore", threshold=70)
        assert result["passed"] is True

    def test_equal_opportunity_violated(self):
        jobs = self._make_jobs([
            (90, "Singapore"), (85, "Singapore"),
            (50, "Remote"), (45, "Remote"),
        ])
        result = equal_opportunity_check(jobs, "Singapore", threshold=70)
        # All local above threshold, no remote above — big gap
        assert result["passed"] is False


# ── Pitch Grounding ──────────────────────────────────────────────────


class TestPitchGrounding:
    def test_grounded_pitch(self):
        resume = {
            "skills": {"technical": ["Python", "AWS"], "soft": [], "certifications": []},
            "experience": [{"title": "Engineer", "company": "Acme Corp"}],
            "contact_info": {"name": "Alice"},
            "years_of_experience": 5,
        }
        job = {"title": "Software Engineer", "company": "BigCo"}
        pitch = "As a Python and AWS engineer with 5 years experience at Acme Corp, I'm excited about the Software Engineer role at BigCo."
        result = verify_pitch_grounding(pitch, resume, job)
        assert result["grounding_score"] > 0.5
        assert len(result["verified_claims"]) > 0
        assert len(result["warnings"]) == 0

    def test_ungrounded_pitch(self):
        resume = {
            "skills": {"technical": ["Java"], "soft": [], "certifications": []},
            "experience": [],
            "years_of_experience": 2,
        }
        job = {"title": "Data Scientist", "company": "DataCo"}
        pitch = "With 10 years of experience in machine learning at Google, I'm the ideal candidate for SomeCo."
        result = verify_pitch_grounding(pitch, resume, job)
        assert len(result["warnings"]) > 0
        # Company mismatch and experience mismatch
        assert any("DataCo" in w or "mismatch" in w.lower() for w in result["warnings"])

    def test_empty_pitch(self):
        result = verify_pitch_grounding("", {}, {})
        assert result["grounding_score"] == 0.0
        assert "Empty pitch text" in result["warnings"]

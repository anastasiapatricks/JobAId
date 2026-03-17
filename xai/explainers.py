"""SHAP-like and LIME-like explainers using skill-triage set logic.

Pure Python — no external ML libraries needed. Operates on the same
candidate_skills vs job_keywords set-intersection logic used by skill_triage.

When structured keywords produce zero overlap, falls back to description-based
keyword extraction so users always get a meaningful explanation.
"""

from itertools import combinations
from typing import Dict, List, Optional


def _match_ratio(skill_set: set, job_keywords: set) -> float:
    """Compute match ratio between a skill set and job keywords."""
    if not job_keywords:
        return 0.0
    return len(skill_set & job_keywords) / len(job_keywords)


def _extract_description_terms(description: str) -> List[str]:
    """Extract meaningful terms from a job description for fallback matching.

    Uses the same _KNOWN_SKILLS list from the job board API so the keyword
    universe is consistent across the pipeline. Falls back to a lightweight
    bigram/trigram scan if the import isn't available.
    """
    if not description:
        return []
    try:
        from tools.job_board_api import _extract_keywords_from_text
        return _extract_keywords_from_text(description)
    except ImportError:
        pass

    # Lightweight fallback: extract 2+ word phrases that look like skills
    import re
    text = description.lower()
    # Common skill-like patterns (tool names, compound terms)
    tokens = re.findall(r"[a-z][a-z0-9.+#/-]{2,}", text)
    return sorted(set(tokens))


def _build_enriched_keywords(
    keywords: List[str],
    description: str,
    candidate_skills: List[str],
) -> tuple:
    """Build an enriched keyword set and track whether enrichment was used.

    Returns (enriched_keywords_list, method_string).
    Only enriches if the base keywords have zero overlap with candidate skills.
    """
    kw_lower = {k.lower().strip() for k in keywords if k}
    skills_lower = {s.lower().strip() for s in candidate_skills if s}

    if kw_lower & skills_lower:
        # There's already overlap — structured keywords are fine
        return keywords, "keywords"

    # Zero overlap — enrich from description
    desc_terms = _extract_description_terms(description)
    if desc_terms:
        combined = sorted(set(keywords) | set(desc_terms))
        combined_lower = {k.lower().strip() for k in combined}
        if combined_lower & skills_lower:
            return combined, "keywords+description"

    # Still no overlap — return originals (will produce zeros, but that's honest)
    return keywords, "keywords" if not desc_terms else "keywords+description"


def shap_skill_attribution(
    candidate_skills: List[str],
    job_keywords: List[str],
    job_description: str = "",
) -> Dict[str, object]:
    """Compute Shapley values for each candidate skill's contribution to match ratio.

    For each skill, we compute its marginal contribution across all possible
    coalitions of the other skills. This gives a fair attribution of how much
    each skill contributes to the overall match score.

    To keep computation tractable, we cap at 12 skills (2^12 = 4096 coalitions).

    When structured keywords have zero overlap with candidate skills, enriches
    the keyword set from the job description so the explanation is meaningful.
    """
    skills_lower = list({s.lower().strip() for s in candidate_skills if s})

    # Enrich keywords from description if structured keywords have no overlap
    enriched_kw, method = _build_enriched_keywords(
        job_keywords, job_description, candidate_skills
    )
    kw_lower = {k.lower().strip() for k in enriched_kw if k}

    if not skills_lower or not kw_lower:
        return {}

    # Cap skills for tractability
    relevant = [s for s in skills_lower if s in kw_lower]
    non_relevant = [s for s in skills_lower if s not in kw_lower]
    # Prioritize relevant skills in the SHAP calculation
    capped = (relevant + non_relevant)[:12]

    shapley_values: Dict[str, float] = {}

    for i, skill in enumerate(capped):
        others = [s for j, s in enumerate(capped) if j != i]
        marginal_sum = 0.0
        num_coalitions = 0

        # Iterate over all subset sizes
        for size in range(len(others) + 1):
            for coalition in combinations(others, size):
                coalition_set = set(coalition)
                v_with = _match_ratio(coalition_set | {skill}, kw_lower)
                v_without = _match_ratio(coalition_set, kw_lower)
                marginal_sum += v_with - v_without
                num_coalitions += 1

        shapley_values[skill] = round(marginal_sum / max(num_coalitions, 1), 4)

    # Sort by absolute contribution descending
    sorted_values = dict(sorted(shapley_values.items(), key=lambda x: -abs(x[1])))

    # Attach metadata so consumers know how the attribution was computed
    sorted_values["_meta"] = {
        "method": method,
        "keyword_count": len(kw_lower),
        "overlap_count": len(set(skills_lower) & kw_lower),
    }

    return sorted_values


def lime_job_explanation(
    candidate_skills: List[str],
    job_keywords: List[str],
    top_n: int = 5,
    job_description: str = "",
) -> List[Dict[str, object]]:
    """LIME-like perturbation: remove one skill at a time, measure match_ratio change.

    Returns top-N most impactful skills with direction:
    - positive impact = having this skill increases the match score
    - the magnitude shows how much the score drops when this skill is removed

    When structured keywords have zero overlap, enriches from description.
    """
    skills_lower = list({s.lower().strip() for s in candidate_skills if s})

    # Enrich keywords from description if structured keywords have no overlap
    enriched_kw, method = _build_enriched_keywords(
        job_keywords, job_description, candidate_skills
    )
    kw_lower = {k.lower().strip() for k in enriched_kw if k}

    if not skills_lower or not kw_lower:
        return []

    full_set = set(skills_lower)
    baseline = _match_ratio(full_set, kw_lower)

    impacts = []
    for skill in skills_lower:
        perturbed = full_set - {skill}
        perturbed_score = _match_ratio(perturbed, kw_lower)
        delta = baseline - perturbed_score  # positive = skill helps
        impacts.append({
            "skill": skill,
            "impact": round(delta, 4),
            "direction": "positive" if delta > 0 else "neutral",
            "baseline_score": round(baseline, 4),
            "perturbed_score": round(perturbed_score, 4),
        })

    # Sort by impact descending, take top N
    impacts.sort(key=lambda x: -abs(x["impact"]))
    result = impacts[:top_n]

    # Attach metadata
    if result:
        result[0]["_meta"] = {
            "method": method,
            "keyword_count": len(kw_lower),
            "overlap_count": len(full_set & kw_lower),
        }

    return result

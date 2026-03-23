"""Fairness checks — Statistical Parity and Equal Opportunity.

Pure Python implementation inspired by AIF360 concepts.
Operates on scored job results to detect location-based bias.
"""

from typing import Any, Dict, List


def statistical_parity_check(
    scored_jobs: List[Dict[str, Any]], candidate_location: str
) -> Dict[str, Any]:
    """Check if job scoring exhibits location bias via Statistical Parity Difference.

    Splits jobs into two groups:
    - local: job location matches candidate_location (case-insensitive substring)
    - remote: job location does not match

    Compares mean scores. If the gap exceeds 10 points, flags potential bias.
    """
    if not scored_jobs or not candidate_location:
        return {
            "test": "statistical_parity",
            "passed": True,
            "local_mean": 0.0,
            "remote_mean": 0.0,
            "gap": 0.0,
            "detail": "Insufficient data for fairness check",
        }

    loc_lower = candidate_location.lower().strip()
    local_scores = []
    remote_scores = []

    for job in scored_jobs:
        score = job.get("score", 0)
        job_loc = (job.get("location") or "").lower()
        if loc_lower in job_loc or job_loc in loc_lower:
            local_scores.append(score)
        else:
            remote_scores.append(score)

    local_mean = sum(local_scores) / max(len(local_scores), 1)
    remote_mean = sum(remote_scores) / max(len(remote_scores), 1)
    gap = abs(local_mean - remote_mean)

    passed = gap <= 10
    detail = (
        f"Local jobs ({len(local_scores)}): mean {local_mean:.1f}, "
        f"Remote jobs ({len(remote_scores)}): mean {remote_mean:.1f}, "
        f"gap {gap:.1f}"
    )
    if not passed:
        detail += " — potential location bias detected"

    return {
        "test": "statistical_parity",
        "passed": passed,
        "local_mean": round(local_mean, 2),
        "remote_mean": round(remote_mean, 2),
        "gap": round(gap, 2),
        "local_count": len(local_scores),
        "remote_count": len(remote_scores),
        "detail": detail,
    }


def equal_opportunity_check(
    scored_jobs: List[Dict[str, Any]],
    candidate_location: str,
    threshold: int = 70,
) -> Dict[str, Any]:
    """Check if selection rate (score >= threshold) is balanced across location groups.

    Equal Opportunity requires that the true positive rate is similar across
    protected groups. Here we proxy it with selection rate above the threshold.
    """
    if not scored_jobs or not candidate_location:
        return {
            "test": "equal_opportunity",
            "passed": True,
            "local_rate": 0.0,
            "remote_rate": 0.0,
            "gap": 0.0,
            "detail": "Insufficient data for fairness check",
        }

    loc_lower = candidate_location.lower().strip()
    local_total = 0
    local_selected = 0
    remote_total = 0
    remote_selected = 0

    for job in scored_jobs:
        score = job.get("score", 0)
        job_loc = (job.get("location") or "").lower()
        if loc_lower in job_loc or job_loc in loc_lower:
            local_total += 1
            if score >= threshold:
                local_selected += 1
        else:
            remote_total += 1
            if score >= threshold:
                remote_selected += 1

    local_rate = local_selected / max(local_total, 1)
    remote_rate = remote_selected / max(remote_total, 1)
    gap = abs(local_rate - remote_rate)

    passed = gap <= 0.2  # 20% gap tolerance (four-fifths rule inspired)
    detail = (
        f"Local selection rate: {local_rate:.0%} ({local_selected}/{local_total}), "
        f"Remote selection rate: {remote_rate:.0%} ({remote_selected}/{remote_total}), "
        f"gap {gap:.0%}"
    )
    if not passed:
        detail += " — potential equal opportunity violation"

    return {
        "test": "equal_opportunity",
        "passed": passed,
        "local_rate": round(local_rate, 4),
        "remote_rate": round(remote_rate, 4),
        "gap": round(gap, 4),
        "threshold": threshold,
        "detail": detail,
    }

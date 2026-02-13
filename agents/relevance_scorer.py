from typing import Dict, Any, List, Tuple

# ---------------------------------------------------------------------------
# Helper function to compute a simple skill-overlap score between resume skills
# and job keywords.
# ---------------------------------------------------------------------------
def _score(skills: List[str], job_keywords: List[str]) -> int:
    # Normalize both lists to lowercase and turn them into sets for fast lookup
    sset = set(s.lower() for s in skills)
    jset = set(k.lower() for k in job_keywords)
    # Compute the intersection (shared skills) and multiply by 10
    # so that each overlapping skill gives 10 points (0–100 scale)
    return int(len(sset & jset) * 10)


# ---------------------------------------------------------------------------
# Main relevance scoring agent
# Given parsed resume info and a list of job listings, it:
#   1. Calculates skill overlap for each job
#   2. Assigns a numeric score (0–100)
#   3. Sorts the jobs by score (descending)
#   4. Returns a compact summary message with the Top 5 results
# ---------------------------------------------------------------------------
def relevance_scorer_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    # Extract resume info and job listings from the conversation state
    resume = state.get("resume_info") or {}
    skills: List[str] = resume.get("skills") or []
    jobs: List[Dict[str, Any]] = state.get("job_listings") or []

    # Prepare a list to store scored results
    scored: List[Dict[str, Any]] = []

    # Precompute a lowercase set of skills for efficiency
    sset = set(s.lower() for s in skills)

    # Iterate over each job and calculate the overlap score
    for j in jobs:
        kws = j.get("keywords", [])
        # Determine which skills overlap between resume and job
        overlap = sorted(sset & set(k.lower() for k in kws))
        # Each overlapping skill contributes 10 points
        score = int(len(overlap) * 10)
        # Store result, keeping both metadata and score
        scored.append({
            **j,
            "score": score,
            "overlap": overlap,
        })

    # Sort by score descending; if equal, sort alphabetically by job title
    scored.sort(key=lambda x: (-x["score"], x["title"]))

    # Prepare a user-facing summary message showing top 5 results
    top5 = scored[:5]
    if top5:
        # Build display lines with job title, company, score, and overlap
        lines = [
            f"{i+1}. {j['title']} @ {j['company']} — {j['score']}/100"
            + (f" (overlap: {', '.join(j['overlap'])})" if j.get('overlap') else "")
            for i, j in enumerate(top5)
        ]
        msg = "Top matches:\n" + "\n".join(lines)
    else:
        msg = "No jobs to score."

    # Return both a message (for chat display) and the full scored list
    return {
        "messages": [{"role": "assistant", "content": msg}],
        "scored_jobs": scored,  # Full detailed results for downstream agents (e.g. pitch generator)
    }

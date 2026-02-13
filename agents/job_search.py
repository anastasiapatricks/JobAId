from typing import Dict, Any, List
from tools.job_scrape import MOCK_JOBS
from utils import debug

def job_search(state: Dict[str, Any]) -> Dict[str, Any]:

    """
    Search for jobs in the mock job list by matching query terms in title or keywords.
    Returns the top 5 matches.
    """
    query = state.get("job_query") or ""
    debug(f"Tool Job Scrape has been called with query: '{query}'")
    query_terms = query.lower().split()

    def matches(job: Dict[str, Any]) -> bool:
        hay = " ".join([job["title"].lower()] + job.get("keywords", []))
        if not query_terms:
            return True
        return any(q in hay for q in query_terms)

    jobs: List[Dict[str, Any]] = [j for j in MOCK_JOBS if matches(j)]
    top_jobs = jobs[:5]

    msg = f"[DEBUG] Job search returning {len(top_jobs)} jobs. Used [TOOL] Job Scrape to find matches."
    return {
        "messages": [{
            "role": "assistant",
            "content": msg
        }],
        "job_listings": top_jobs,
    }

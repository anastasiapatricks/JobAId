"""Adzuna job board API integration with MOCK_JOBS fallback."""

from typing import List, Dict, Any
import httpx
from config.settings import settings
from tools.job_scrape import MOCK_JOBS
from utils import debug


def _normalize_adzuna_job(raw: dict) -> Dict[str, Any]:
    """Convert Adzuna API response to internal JobListing format."""
    return {
        "title": raw.get("title", ""),
        "company": raw.get("company", {}).get("display_name", "Unknown"),
        "location": raw.get("location", {}).get("display_name", ""),
        "description": raw.get("description", ""),
        "keywords": [],  # Adzuna doesn't provide keywords; extracted downstream
        "salary_min": raw.get("salary_min"),
        "salary_max": raw.get("salary_max"),
        "url": raw.get("redirect_url", ""),
        "source": "adzuna",
    }


_STOP_WORDS = {
    "in", "for", "a", "an", "the", "and", "or", "of", "at", "to", "with",
    "on", "is", "as", "by", "about", "into", "from", "that", "this",
    "i", "am", "looking", "searching", "seeking", "want", "need", "find",
    "me", "my", "role", "position", "job", "jobs", "career", "work",
}


def _simplify_query(query: str) -> str:
    """Strip filler/stop words, keeping meaningful job-related terms."""
    words = query.lower().split()
    keywords = [w for w in words if w not in _STOP_WORDS and len(w) > 1]
    return " ".join(keywords) if keywords else query


def _search_adzuna_once(query: str, location: str, num_results: int) -> List[Dict[str, Any]]:
    """Single Adzuna API call. Returns normalized jobs or empty list."""
    country = settings.adzuna_country
    url = f"{settings.adzuna_base_url}/jobs/{country}/search/1"

    params = {
        "app_id": settings.adzuna_app_id,
        "app_key": settings.adzuna_api_key,
        "what": query,
        "results_per_page": num_results,
        "content-type": "application/json",
    }
    if location:
        params["where"] = location

    try:
        debug(f"Adzuna: searching for '{query}' in {country}")
        resp = httpx.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        jobs = [_normalize_adzuna_job(r) for r in results]
        debug(f"Adzuna: found {len(jobs)} results")
        return jobs
    except Exception as exc:
        debug(f"Adzuna API error: {exc}")
        return []


def search_adzuna(query: str, location: str = "", num_results: int = 10) -> List[Dict[str, Any]]:
    """Search Adzuna API for job listings.

    Tries the cleaned query first, then progressively broadens by dropping
    trailing keywords until results are found or keywords are exhausted.
    """
    if not settings.adzuna_app_id or not settings.adzuna_api_key:
        debug("Adzuna: no API credentials configured, skipping")
        return []

    clean = _simplify_query(query)
    keywords = clean.split()

    # Try full query, then progressively drop the last keyword to broaden
    while keywords:
        attempt = " ".join(keywords)
        jobs = _search_adzuna_once(attempt, location, num_results)
        if jobs:
            return jobs
        keywords.pop()
        if keywords:
            debug(f"Adzuna: 0 results, broadening to '{' '.join(keywords)}'")

    return []


def search_jobs(query: str, location: str = "", num_results: int = 10) -> List[Dict[str, Any]]:
    """Search for jobs — tries Adzuna first, falls back to MOCK_JOBS.

    Returns list of normalized job dicts with a 'source' field.
    """
    # Try Adzuna first
    jobs = search_adzuna(query, location, num_results)
    if jobs:
        return jobs

    # Fallback to MOCK_JOBS
    debug("Job search: falling back to MOCK_JOBS")
    query_terms = query.lower().split()

    def matches(job: Dict[str, Any]) -> bool:
        hay = " ".join([job["title"].lower()] + job.get("keywords", []))
        if not query_terms:
            return True
        return any(q in hay for q in query_terms)

    matched = [
        {**j, "source": "mock", "description": f"Mock job listing for {j['title']} at {j['company']}", "salary_min": None, "salary_max": None, "url": ""}
        for j in MOCK_JOBS if matches(j)
    ]
    return matched[:num_results]

"""Adzuna job board API integration with MOCK_JOBS fallback."""

import json
import time
import logging
from typing import List, Dict, Any
from datetime import datetime, timezone
import httpx
from config.settings import settings
from tools.job_scrape import MOCK_JOBS
from utils import debug

_api_logger = logging.getLogger("jobaid.external")


# Common technical skills/tools to extract from job descriptions
_KNOWN_SKILLS = {
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "golang", "rust",
    "ruby", "php", "swift", "kotlin", "scala", "r", "sql", "bash", "powershell",
    "docker", "kubernetes", "aws", "azure", "gcp", "terraform", "ansible", "jenkins",
    "git", "linux", "windows", "macos", "react", "angular", "vue", "node.js", "nodejs",
    "django", "flask", "fastapi", "spring", "spring boot",
    "machine learning", "deep learning", "nlp", "computer vision",
    "ida pro", "ghidra", "x64dbg", "yara", "wireshark", "burp suite", "nmap",
    "malware analysis", "reverse engineering", "incident response", "digital forensics",
    "threat intelligence", "penetration testing", "vulnerability research",
    "siem", "splunk", "elastic", "mitre att&ck", "osint",
    "ci/cd", "devops", "mlops", "agile", "scrum",
    "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
    "spark", "airflow", "kafka", "hadoop",
    "cybersecurity", "network security", "cloud security", "application security",
    "soc", "dfir", "threat hunting", "red team", "blue team",
}


def _extract_keywords_from_text(text: str) -> List[str]:
    """Extract known technical skills/tools from job description text."""
    text_lower = text.lower()
    found = []
    for skill in _KNOWN_SKILLS:
        if skill in text_lower:
            found.append(skill)
    return sorted(found)


def _normalize_adzuna_job(raw: dict) -> Dict[str, Any]:
    """Convert Adzuna API response to internal JobListing format."""
    desc = raw.get("description", "")
    title = raw.get("title", "")
    keywords = _extract_keywords_from_text(f"{title} {desc}")
    return {
        "title": title,
        "company": raw.get("company", {}).get("display_name", "Unknown"),
        "location": raw.get("location", {}).get("display_name", ""),
        "description": desc,
        "keywords": keywords,
        "salary_min": raw.get("salary_min"),
        "salary_max": raw.get("salary_max"),
        "url": raw.get("redirect_url", ""),
        "created_at": raw.get("created"),
        "category": raw.get("category", {}).get("label", ""),
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
        "max_days_old": 90,
        "sort_by": "date",
        "content-type": "application/json",
    }
    if location:
        params["where"] = location

    start = time.time()
    try:
        debug(f"Adzuna: searching for '{query}' in {country}")
        resp = httpx.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        jobs = [_normalize_adzuna_job(r) for r in results]
        latency_ms = round((time.time() - start) * 1000, 1)
        _api_logger.info(json.dumps({
            "event": "external_api_call",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "adzuna",
            "operation": "search",
            "status": "success",
            "latency_ms": latency_ms,
            "result_count": len(jobs),
        }))
        debug(f"Adzuna: found {len(jobs)} results")
        return jobs
    except Exception as exc:
        latency_ms = round((time.time() - start) * 1000, 1)
        _api_logger.error(json.dumps({
            "event": "external_api_call",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "adzuna",
            "operation": "search",
            "status": "error",
            "latency_ms": latency_ms,
            "error": str(exc)[:200],
        }))
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

    # Fallback to MOCK_JOBS — score by keyword overlap, not position
    debug("Job search: falling back to MOCK_JOBS")
    query_terms = [t for t in query.lower().split() if t not in _STOP_WORDS]

    def relevance_score(job: Dict[str, Any]) -> int:
        hay = " ".join([job["title"].lower()] + job.get("keywords", []))
        if not query_terms:
            return 1
        return sum(1 for q in query_terms if q in hay)

    scored = []
    for j in MOCK_JOBS:
        score = relevance_score(j)
        if score > 0:
            scored.append((score, {
                **j,
                "source": "mock",
                "description": f"Mock job listing for {j['title']} at {j['company']}",
                "salary_min": None,
                "salary_max": None,
                "url": "",
            }))

    # Sort by relevance score descending so best matches come first
    scored.sort(key=lambda x: x[0], reverse=True)
    return [job for _, job in scored[:num_results]]

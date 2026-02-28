"""Tavily web search helpers for market intelligence and company research."""

from typing import List

from utils import debug


def _get_client():
    """Return a TavilyClient if the API key is configured and SDK installed, else None."""
    from config.settings import settings

    if not settings.tavily_api_key:
        debug("Tavily: no API key configured, skipping web search")
        return None
    try:
        from tavily import TavilyClient

        return TavilyClient(api_key=settings.tavily_api_key)
    except ImportError:
        debug("Tavily: tavily-python not installed, skipping web search")
        return None


def _format_results(results: list, snippet_len: int = 200) -> str:
    """Format Tavily search results into a context string."""
    lines = []
    for r in results:
        title = r.get("title", "")
        url = r.get("url", "")
        snippet = (r.get("content") or "")[:snippet_len]
        lines.append(f"- {title} | {url}\n  {snippet}")
    return "\n".join(lines)


def search_courses(skill_gaps: List[str], job_query: str) -> str:
    """Search for online courses/certifications relevant to skill gaps."""
    client = _get_client()
    if client is None:
        return ""
    skills_text = ", ".join(skill_gaps[:5]) if skill_gaps else job_query
    query = f"best online courses certifications for {skills_text} {job_query}"
    try:
        debug(f"Tavily courses search: {query[:80]}")
        response = client.search(query=query, search_depth="basic", max_results=5)
        results = response.get("results", [])
        if not results:
            return ""
        return "Web search — recommended courses:\n" + _format_results(results)
    except Exception as exc:
        debug(f"Tavily courses search error: {exc}")
        return ""


def search_trends(job_query: str) -> str:
    """Search for current industry trends related to the job query."""
    client = _get_client()
    if client is None:
        return ""
    query = f"latest industry trends hiring outlook {job_query} 2025 2026"
    try:
        debug(f"Tavily trends search: {query[:80]}")
        response = client.search(query=query, search_depth="basic", max_results=4)
        results = response.get("results", [])
        if not results:
            return ""
        return "Web search — industry trends:\n" + _format_results(results)
    except Exception as exc:
        debug(f"Tavily trends search error: {exc}")
        return ""


def search_salary(job_query: str, years_exp: int | None) -> str:
    """Search for salary benchmarks (Singapore-focused)."""
    client = _get_client()
    if client is None:
        return ""
    exp_text = f"{years_exp} years experience" if years_exp else ""
    query = f"{job_query} salary range Singapore {exp_text} 2025 2026"
    try:
        debug(f"Tavily salary search: {query[:80]}")
        response = client.search(query=query, search_depth="basic", max_results=3)
        results = response.get("results", [])
        if not results:
            return ""
        return "Web search — salary benchmarks:\n" + _format_results(results)
    except Exception as exc:
        debug(f"Tavily salary search error: {exc}")
        return ""


def search_company(company_name: str) -> str:
    """Search the web for company information (about, mission, products, culture)."""
    client = _get_client()
    if client is None:
        return ""
    if not company_name:
        return ""
    query = f"{company_name} company about mission products culture"
    try:
        debug(f"Tavily company search: {query[:80]}")
        response = client.search(query=query, search_depth="basic", max_results=3)
        results = response.get("results", [])
        if not results:
            return ""
        return "Web search — company info:\n" + _format_results(results, snippet_len=300)
    except Exception as exc:
        debug(f"Tavily company search error: {exc}")
        return ""

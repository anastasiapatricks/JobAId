"""Adzuna job board API integration with MOCK_JOBS fallback."""

import json
import time
import logging
from typing import List, Dict, Any
from datetime import datetime, timezone
import httpx
from config.settings import settings
from tools.job_scrape import MOCK_JOBS
from utils import debug, _log_context

_api_logger = logging.getLogger("jobaid.external")


# Known skills/tools across industries for keyword extraction.
# Rules: >= 3 chars, won't false-positive on common English words.
_KNOWN_SKILLS = {
    # --- TECH: Programming Languages ---
    "python", "java", "javascript", "typescript", "c++", "c#", "golang", "rust",
    "ruby", "php", "swift", "kotlin", "scala", "sql", "bash", "powershell",
    "html", "css", "matlab", "vba", "perl", "lua", "dart", "solidity",
    # --- TECH: Frameworks & Libraries ---
    "react", "angular", "vue", "node.js", "nodejs", "django", "flask", "fastapi",
    "spring boot", ".net", "express.js", "next.js", "flutter", "react native",
    "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy",
    # --- TECH: Infrastructure & Cloud ---
    "docker", "kubernetes", "aws", "azure", "gcp", "terraform", "ansible",
    "jenkins", "git", "linux", "windows", "vmware", "openstack",
    "ci/cd", "devops", "mlops", "microservices", "serverless", "api",
    # --- TECH: Databases & Data ---
    "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "oracle",
    "sql server", "dynamodb", "cassandra", "neo4j", "snowflake", "bigquery",
    "spark", "airflow", "kafka", "hadoop", "etl", "data pipeline",
    "data warehouse", "data lake", "data modeling", "data governance",
    # --- TECH: AI/ML ---
    "machine learning", "deep learning", "nlp", "computer vision",
    "generative ai", "llm", "reinforcement learning", "neural network",
    # --- CYBERSECURITY ---
    "ida pro", "ghidra", "x64dbg", "windbg", "binary ninja", "yara",
    "wireshark", "burp suite", "nmap", "volatility", "velociraptor",
    "splunk", "elastic stack", "elk", "encase", "axiom",
    "malware analysis", "malware", "reverse engineering", "incident response",
    "digital forensics", "forensics", "threat intelligence", "threat hunting",
    "penetration testing", "vulnerability research", "vulnerability assessment",
    "siem", "mitre att&ck", "osint", "soc", "dfir", "red team", "blue team",
    "cybersecurity", "network security", "cloud security", "application security",
    "security operations", "security monitoring", "intrusion detection",
    "log analysis", "network forensics", "memory forensics", "disk forensics",
    "iso 27001", "nist", "gdpr", "pci dss", "zero trust",
    # --- FINANCE & ACCOUNTING ---
    "financial analysis", "financial modeling", "valuation", "risk management",
    "portfolio management", "derivatives", "fixed income", "equities",
    "accounting", "auditing", "bookkeeping", "tax", "gaap", "ifrs",
    "bloomberg", "reuters", "excel", "financial reporting", "budgeting",
    "forecasting", "credit analysis", "compliance", "aml", "kyc",
    "investment banking", "private equity", "venture capital", "hedge fund",
    "cfa", "acca", "cpa", "fmva",
    # --- MARKETING & SALES ---
    "digital marketing", "seo", "sem", "social media marketing", "content marketing",
    "email marketing", "marketing automation", "google analytics", "google ads",
    "facebook ads", "hubspot", "salesforce", "crm", "lead generation",
    "brand management", "market research", "copywriting", "public relations",
    "influencer marketing", "affiliate marketing", "a/b testing",
    "account management", "business development", "negotiation",
    "cold calling", "pipeline management", "sales strategy",
    # --- DESIGN & CREATIVE ---
    "figma", "adobe xd", "sketch", "photoshop", "illustrator", "indesign",
    "after effects", "premiere pro", "blender", "autocad", "solidworks",
    "ui design", "ux design", "ux research", "prototyping", "wireframing",
    "graphic design", "motion graphics", "3d modeling", "typography",
    # --- PROJECT MANAGEMENT & OPERATIONS ---
    "agile", "scrum", "kanban", "waterfall", "lean", "six sigma",
    "project management", "program management", "pmp", "prince2",
    "jira", "confluence", "asana", "trello", "monday.com",
    "stakeholder management", "change management", "risk assessment",
    "process improvement", "supply chain", "logistics", "procurement",
    "inventory management", "warehouse management", "vendor management",
    # --- HR & PEOPLE ---
    "recruitment", "talent acquisition", "onboarding", "performance management",
    "compensation and benefits", "employee relations", "hris", "workday",
    "succession planning", "learning and development", "org design",
    # --- HEALTHCARE & LIFE SCIENCES ---
    "clinical trials", "gmp", "gcp", "pharmacovigilance", "regulatory affairs",
    "medical devices", "fda", "ema", "biostatistics", "epidemiology",
    "electronic health records", "hl7", "fhir", "dicom",
    # --- ENGINEERING (Non-software) ---
    "mechanical engineering", "electrical engineering", "civil engineering",
    "chemical engineering", "structural analysis", "finite element analysis",
    "plc programming", "scada", "control systems", "hvac",
    "cad", "cam", "cnc", "robotics", "automation",
    # --- LEGAL & COMPLIANCE ---
    "contract law", "corporate law", "intellectual property", "litigation",
    "due diligence", "regulatory compliance", "legal research",
    "anti-money laundering", "sanctions screening", "data privacy",
    # --- COMMUNICATION & SOFT SKILLS ---
    "leadership", "team management", "cross-functional collaboration",
    "presentation skills", "public speaking", "technical writing",
    "problem solving", "critical thinking", "strategic planning",
    "client relationship", "stakeholder engagement",
    # --- DATA & ANALYTICS ---
    "data analysis", "data visualization", "business intelligence",
    "tableau", "power bi", "looker", "qlik", "sas", "spss",
    "statistical analysis", "hypothesis testing", "regression analysis",
    "a/b testing", "predictive modeling",
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
        resp = httpx.get(url, params=params, timeout=10, verify=False)
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
            **_log_context(),
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
            **_log_context(),
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

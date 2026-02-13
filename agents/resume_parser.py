# agents/resume_parser.py
import re
from typing import Dict, Any

def load_resume_from_file(path: str) -> str:
    """Read and return plain text content from a resume file."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()

def resume_parser(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse resume inputted by user.
    """

    text = (state.get("resume_text") or "").strip()
    info = {
        "name": None,
        "years_experience": None,
        "skills": [],
    }

    # naive extractions
    m = re.search(r"(?:Name|Candidate)[:\-]\s*([A-Za-z .'-]{2,})", text, re.I)
    if m:
        info["name"] = m.group(1).strip()

    m = re.search(r"(\d+)\s*\+?\s*(?:years|yrs)", text, re.I)
    if m:
        info["years_experience"] = int(m.group(1))

    # skill bag from common tech; extend as needed
    SKILLS = [
        "python","java","javascript","typescript","c++","spring","spring boot",
        "angular","react","sql","postgres","mysql","db2","docker","kubernetes",
        "aws","gcp","azure","git","maven","jest","junit","redis","microservices"
    ]
    lower = text.lower()
    found = {s for s in SKILLS if s in lower}
    info["skills"] = sorted(found)

    msg = f"Parsed resume. Skills: {', '.join(info['skills']) or '—'}. Experience: {info['years_experience'] or '—'} yrs."
    return {
        "messages": [{"role": "assistant", "content": msg}],
        "resume_info": info,
    }

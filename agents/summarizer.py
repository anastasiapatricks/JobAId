"""Grounded summarizer with explainability — feeds full session state to the LLM."""

import json
from typing import Dict, Any

from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

from config.settings import settings
from config.prompts import SUMMARIZER_SYSTEM
from utils import debug


# Keys to exclude from the context — internal/noisy fields the LLM doesn't need
_EXCLUDE_KEYS = {
    "session_id",
    "messages",
    "current_stage",
    "stage_history",
    "iteration_count",
    "max_iterations",
    "requires_human_approval",
    "human_feedback",
    "resume_text",
    "resume_debiased",
}


def _build_context(state: Dict[str, Any]) -> str:
    """Serialize the relevant parts of state as JSON for the LLM."""
    filtered = {k: v for k, v in state.items() if k not in _EXCLUDE_KEYS and v}
    return json.dumps(filtered, indent=2, default=str)


def summarizer(state: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a grounded summary from the full session state."""
    context = _build_context(state)

    try:
        llm = ChatOpenAI(model=settings.default_model, temperature=0)
        response = llm.invoke([
            SystemMessage(content=SUMMARIZER_SYSTEM),
            HumanMessage(content=f"Session data:\n\n{context}\n\nGenerate the final report."),
        ])
        summary_text = response.content.strip()
    except Exception as exc:
        debug(f"Summarizer LLM error: {exc}")
        summary_text = f"=== JobAId Summary ===\n\n{context}"

    # Append decision log if present
    log = state.get("decision_log") or []
    log_text = ""
    if log:
        log_text = "\n\n--- Decision Log ---\n" + "\n".join(
            f"[{e.get('stage')}] {e.get('action')}: {e.get('reasoning')}" for e in log
        )

    return {
        "messages": [{"role": "assistant", "content": "[Summarizer] Final report generated."}],
        "summary": summary_text + log_text,
    }

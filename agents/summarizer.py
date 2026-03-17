"""Grounded summarizer with explainability — feeds full session state to the LLM."""

import json
import logging
from typing import Dict, Any

from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

from config.settings import settings
from config.prompts import SUMMARIZER_SYSTEM, SUMMARIZER_PROMPT_VERSION
from xai.trace import create_trace
from guardrails.output_filter import check_grounding
from guardrails.model_router import get_model_for_task
from utils import debug
from utils.llm_logger import logged_invoke

_guard_logger = logging.getLogger("jobaid.guardrails")


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
        from agents.orchestrator import get_autonomy
        if not get_autonomy().record_llm_call():
            raise RuntimeError("LLM call limit exceeded")
        llm = ChatOpenAI(model=get_model_for_task("summarization"), temperature=0)
        response = logged_invoke(llm, [
            SystemMessage(content=SUMMARIZER_SYSTEM),
            HumanMessage(content=f"Session data:\n\n{context}\n\nGenerate the final report."),
        ], "summarization")
        summary_text = response.content.strip()
    except Exception as exc:
        debug(f"Summarizer LLM error: {exc}")
        summary_text = f"=== JobAId Summary ===\n\n{context}"

    # Grounding check — verify summary references state data
    grounding_score = check_grounding(summary_text, state)
    from datetime import datetime, timezone
    _guard_logger.info(json.dumps({
        "event": "grounding_check",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": "summarizer",
        "grounding_score": round(grounding_score, 2),
        "passed": grounding_score >= 0.5,
    }))
    if grounding_score < 0.5:
        _guard_logger.warning(json.dumps({
            "event": "guardrail_triggered",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "guardrail": "grounding_check",
            "agent": "summarizer",
            "grounding_score": round(grounding_score, 2),
            "detail": "Summary may contain ungrounded claims",
        }))

    # Append decision log if present
    log = state.get("decision_log") or []
    log_text = ""
    if log:
        log_text = "\n\n--- Decision Log ---\n" + "\n".join(
            f"[{e.get('stage')}] {e.get('action')}: {e.get('reasoning')}" for e in log
        )

    # --- XAI: Explainability trace ---
    xai_warnings = []
    if grounding_score < 0.5:
        xai_warnings.append(f"Low grounding score ({grounding_score:.2f})")
    explainability_trace = create_trace(
        agent_name="summarizer",
        prompt_version=SUMMARIZER_PROMPT_VERSION,
        confidence=grounding_score,
        reasoning=f"Grounding score {grounding_score:.2f}; {len(log)} decision log entries",
        grounding_score=grounding_score,
        sources_consulted=["session_state", "decision_log"],
        warnings=xai_warnings,
    ).to_dict()

    return {
        "messages": [{"role": "assistant", "content": "[Summarizer] Final report generated."}],
        "summary": summary_text + log_text,
        "explainability_trace": explainability_trace,
    }

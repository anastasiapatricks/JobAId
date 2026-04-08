"""Grounded summarizer with explainability — feeds full session state to the LLM."""

import json
import logging
from typing import Dict, Any

from langchain_core.messages import SystemMessage, HumanMessage


from guardrails.output_filter import check_grounding, scan_output_for_pii
from config.prompts import SUMMARIZER_SYSTEM, SUMMARIZER_PROMPT_VERSION
from xai.trace import create_trace
from guardrails.output_filter import check_grounding
from guardrails.model_router import get_model_for_task
from guardrails.llm_factory import get_llm
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
    """Serialize the relevant parts of state as JSON for the LLM.

    Strips contact PII (name, email, phone) from resume_info before sending
    to the LLM. These are repopulated in the summary after generation.
    """
    filtered = {k: v for k, v in state.items() if k not in _EXCLUDE_KEYS and v}

    # Strip contact PII — never send name/email/phone to LLM
    if "resume_info" in filtered and isinstance(filtered["resume_info"], dict):
        filtered["resume_info"] = _strip_contact_pii(filtered["resume_info"])

    return json.dumps(filtered, indent=2, default=str)


def _strip_contact_pii(resume_info: Dict[str, Any]) -> Dict[str, Any]:
    """Remove name, email, phone from resume_info for LLM context."""
    info = {k: v for k, v in resume_info.items()}
    contact = info.get("contact_info", {})
    if isinstance(contact, dict):
        info["contact_info"] = {
            k: v for k, v in contact.items()
            if k not in ("name", "email", "phone")
        }
    return info


def _get_candidate_name(state: Dict[str, Any]) -> str:
    """Extract candidate name from state (for post-processing, never sent to LLM)."""
    info = state.get("resume_info") or {}
    contact = info.get("contact_info", {}) if isinstance(info, dict) else {}
    return contact.get("name", "") if isinstance(contact, dict) else ""


def summarizer(state: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a grounded summary from the full session state."""
    context = _build_context(state)

    try:
        from agents.orchestrator import get_autonomy
        if not get_autonomy().record_llm_call():
            raise RuntimeError("LLM call limit exceeded")
        llm = get_llm(model=get_model_for_task("summarization"), temperature=0, task_type="summarization")
        response = logged_invoke(llm, [
            SystemMessage(content=SUMMARIZER_SYSTEM),
            HumanMessage(content=f"Session data:\n\n{context}\n\nGenerate the final report."),
        ], "summarization")
        summary_text = response.content.strip()

        # Scan summary for PII leakage and redact if needed
        is_safe, leaked_pii = scan_output_for_pii(summary_text)
        if not is_safe:
            debug(f"Summarizer: PII leakage detected in summary ({len(leaked_pii)} entities), redacting...")
            # Redact only the sensitive entities that scan_output_for_pii flagged,
            # NOT all NER entities (which would nuke company names, locations, etc.)
            # Deduplicate overlapping spans to avoid garbled output like "re*]"
            sorted_pii = sorted(leaked_pii, key=lambda e: e["start"], reverse=True)
            prev_start = len(summary_text)
            for entity in sorted_pii:
                if entity["end"] > prev_start:
                    continue  # skip overlapping span
                summary_text = (
                    summary_text[:entity["start"]]
                    + "[REDACTED]"
                    + summary_text[entity["end"]:]
                )
                prev_start = entity["start"]

    except Exception as exc:
        debug(f"Summarizer LLM error: {exc}")
        summary_text = f"=== JobAId Summary ===\n\n{context}"

    # Post-processing: repopulate candidate name (same pattern as pitch generator)
    candidate_name = _get_candidate_name(state)
    if candidate_name:
        import re
        # Replace common placeholder patterns the LLM may use
        for pattern in [r"\[Candidate Name\]", r"\[Your Name\]", r"\[Name\]"]:
            summary_text = re.sub(pattern, candidate_name, summary_text, flags=re.IGNORECASE)

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

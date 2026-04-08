"""FSM-based orchestrator — replaces the old coordinator + participant."""

import json
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from langchain.schema import SystemMessage, HumanMessage

from models.state import JobAIdState, OrchestratorStage
from guardrails.bounded_autonomy import BoundedAutonomy
from guardrails.input_filter import spotlight_wrap
from guardrails.model_router import get_model_for_task
from guardrails.llm_factory import get_llm
from config.settings import settings
from config.prompts import ORCHESTRATOR_ROUTER_SYSTEM, ORCHESTRATOR_PROMPT_VERSION
from xai.trace import create_trace
from utils import debug, get_latest_results
from utils.llm_logger import logged_invoke

# Valid FSM transitions: current_stage → set of allowed next stages
TRANSITIONS: Dict[str, list] = {
    "intake": ["parsing"],
    "parsing": ["parsing_review", "discovery"],
    "parsing_review": ["discovery"],
    "discovery": ["discovery_review", "market_intel"],
    "discovery_review": ["market_intel"],
    "market_intel": ["pitching"],
    "pitching": ["pitch_review", "summarizing"],
    "pitch_review": ["summarizing"],
    "summarizing": ["complete"],
    "complete": [],
    "error": ["intake"],
}

# Which stages are actual agent work vs HITL review
AGENT_STAGES = {"parsing", "discovery", "market_intel", "pitching", "summarizing"}
REVIEW_STAGES = {"parsing_review", "discovery_review", "pitch_review"}

# Shared bounded-autonomy tracker (reset per session via graph)
_autonomy = BoundedAutonomy()


def get_autonomy() -> BoundedAutonomy:
    return _autonomy


def reset_autonomy():
    global _autonomy
    _autonomy = BoundedAutonomy()


def _log_decision(state: JobAIdState, stage: str, action: str, reasoning: str) -> list:
    """Append to the decision log and return updated list."""
    log = list(state.get("decision_log") or [])
    log.append({
        "stage": stage,
        "action": action,
        "reasoning": reasoning,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    return log


def _is_stage_complete(state: JobAIdState, stage: str) -> bool:
    """Check whether the outputs required by a stage are present."""
    latest = get_latest_results(state)
    if stage == "parsing":
        return bool(latest.get("resume_info") or state.get("resume_info"))
    if stage == "discovery":
        return bool(latest.get("scored_jobs") or state.get("scored_jobs"))
    if stage == "market_intel":
        return bool(latest.get("skill_gaps") or state.get("skill_gaps"))
    if stage == "pitching":
        return bool(latest.get("final_pitch") or state.get("final_pitch"))
    if stage == "summarizing":
        return bool(latest.get("summary") or state.get("summary"))
    # Review stages are "complete" once human feedback arrives or is skipped
    if stage in REVIEW_STAGES:
        return True
    return True


def determine_next_stage(state: JobAIdState) -> Dict[str, Any]:
    """Orchestrator node: decide the next stage based on current state.

    Returns a partial state update with FSM bookkeeping.
    """
    current = state.get("current_stage", "intake")
    iteration = state.get("iteration_count", 0) + 1
    autonomy = get_autonomy()

    # Bounded autonomy: iteration limit
    if not autonomy.check_iteration_limit(iteration):
        debug(f"Orchestrator: iteration limit ({autonomy.max_iterations}) reached — forcing complete")
        return {
            "current_stage": "error",
            "iteration_count": iteration,
            "decision_log": _log_decision(state, current, "force_complete", "Max iterations reached"),
            "errors": list(state.get("errors") or []) + [{"stage": current, "error": "Max iterations reached"}],
        }

    # If stage work is done, advance
    allowed = TRANSITIONS.get(current, [])
    if not allowed:
        # Already at terminal state
        return {"current_stage": current, "iteration_count": iteration}

    # Skip optional review stages in non-HITL mode
    next_stage: Optional[str] = None
    requires_review = state.get("requires_human_approval", False)

    for candidate in allowed:
        if candidate in REVIEW_STAGES and not requires_review:
            continue
        next_stage = candidate
        break

    if next_stage is None:
        # All candidates were skipped reviews — go deeper in allowed list
        # This shouldn't happen with correct transitions, but fallback to first non-review
        for candidate in allowed:
            if candidate not in REVIEW_STAGES:
                next_stage = candidate
                break

    if next_stage is None:
        next_stage = "complete"

    debug(f"Orchestrator: {current} → {next_stage}")

    stage_history = list(state.get("stage_history") or [])
    stage_history.append({"from": current, "to": next_stage, "iteration": iteration})

    return {
        "current_stage": next_stage,
        "iteration_count": iteration,
        "stage_history": stage_history,
        "decision_log": _log_decision(state, current, "advance", f"{current} → {next_stage}"),
    }


def handle_stage_error(state: JobAIdState, stage: str, error: str) -> Dict[str, Any]:
    """Handle an error in a stage — retry or skip with degraded output."""
    autonomy = get_autonomy()
    errors = list(state.get("errors") or [])
    errors.append({"stage": stage, "error": error})
    fallback_used = list(state.get("fallback_used") or [])

    if autonomy.record_stage_retry(stage):
        debug(f"Orchestrator: retrying stage {stage} (attempt {autonomy.get_stage_retries(stage)})")
        return {
            "errors": errors,
            "decision_log": _log_decision(state, stage, "retry", f"Error: {error}"),
        }
    else:
        # Max retries exceeded — skip stage
        debug(f"Orchestrator: skipping stage {stage} after max retries")
        fallback_used.append(stage)
        # Advance past this stage
        allowed = TRANSITIONS.get(stage, [])
        next_stage = "error"
        for candidate in allowed:
            if candidate not in REVIEW_STAGES:
                next_stage = candidate
                break

        return {
            "current_stage": next_stage,
            "errors": errors,
            "fallback_used": fallback_used,
            "decision_log": _log_decision(state, stage, "skip", f"Max retries exceeded: {error}"),
        }


def _build_state_summary(state: dict) -> str:
    """Build a human-readable summary of what data exists in the state."""
    parts = []
    latest = get_latest_results(state)

    resume_info = latest.get("resume_info") or state.get("resume_info")
    if resume_info:
        skills = (resume_info.get("skills") or {}).get("technical", [])
        parts.append(f"Resume parsed, skills: {', '.join(skills[:8])}")
    else:
        parts.append("Resume: not yet parsed")

    scored_jobs = latest.get("scored_jobs") or state.get("scored_jobs") or []
    if scored_jobs:
        parts.append(f"Scored jobs ({len(scored_jobs)} found):")
        for i, job in enumerate(scored_jobs):
            title = job.get("title", "Unknown")
            company = job.get("company", "Unknown")
            score = job.get("score", "?")
            parts.append(f"  [{i}] {title} at {company} (score: {score})")
    else:
        parts.append("Scored jobs: none yet")

    if latest.get("skill_gaps") or state.get("skill_gaps"):
        parts.append("Market intelligence: available")
    else:
        parts.append("Market intelligence: not yet run")

    if latest.get("final_pitch") or state.get("final_pitch"):
        parts.append("Cover letter/pitch: generated")
    else:
        parts.append("Cover letter/pitch: not yet generated")

    if latest.get("summary") or state.get("summary"):
        parts.append("Summary: generated")
    else:
        parts.append("Summary: not yet generated")

    return "\n".join(parts)


def _parse_router_json(text: str) -> dict:
    """Extract JSON from LLM response, handling markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    return json.loads(text)


def interpret_user_intent(user_message: str, state: dict) -> dict:
    """Use LLM to interpret user message and decide which agent to run.

    Includes recent conversation history so the LLM can resolve references
    like "yes", "do that", "the second one", etc.

    Returns dict with: action, response_text, parameters.
    """
    state_summary = _build_state_summary(state)
    system_prompt = ORCHESTRATOR_ROUTER_SYSTEM.format(state_summary=state_summary)

    # LLM call limit check
    if not _autonomy.record_llm_call():
        return {
            "action": "chitchat",
            "response_text": "Session limit reached. Please start a new session.",
            "parameters": {},
        }

    llm = get_llm(
        model=get_model_for_task("orchestration"),
        temperature=0.1,
        task_type="orchestration"
    )

    # Build message list with recent conversation history for context
    messages = [SystemMessage(content=system_prompt)]

    # Include last few conversation turns so the LLM can resolve
    # short replies like "yes", "do that", "the second one"
    recent_messages = (state.get("messages") or [])[-6:]
    for msg in recent_messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if not content:
            continue
        if role == "user":
            messages.append(HumanMessage(content=content))
        else:
            from langchain_core.messages import AIMessage
            messages.append(AIMessage(content=content))

    # Add the current user message with a JSON reminder since conversation
    # history can cause the model to drift into plain-text chat mode
    wrapped = spotlight_wrap(user_message)
    messages.append(HumanMessage(content=f"{wrapped}\n\nRespond with ONLY valid JSON matching the Response Format above."))

    debug(f"Orchestrator router: interpreting '{user_message}' (with {len(recent_messages)} history msgs)")
    response = logged_invoke(llm, messages, "intent_routing")

    try:
        result = _parse_router_json(response.content)
    except (json.JSONDecodeError, ValueError):
        debug(f"Orchestrator router: failed to parse JSON, defaulting to chitchat")
        result = {
            "action": "chitchat",
            "response_text": response.content,
            "parameters": {},
        }

    # Ensure required fields
    result.setdefault("action", "chitchat")
    result.setdefault("response_text", "")
    result.setdefault("parameters", {})

    # --- XAI: Explainability trace for intent routing ---
    action = result["action"]
    routing_confidence = 0.9 if action != "chitchat" else 0.6
    result["explainability_trace"] = create_trace(
        agent_name="orchestrator",
        prompt_version=ORCHESTRATOR_PROMPT_VERSION,
        confidence=routing_confidence,
        reasoning=f"Routed '{user_message[:50]}' → {action}",
        feature_attributions={"action": action, "parameters": result["parameters"]},
        sources_consulted=["conversation_history", "state_summary"],
        warnings=["Fallback to chitchat (ambiguous intent)"] if action == "chitchat" and not result["response_text"] else [],
    ).to_dict()

    debug(f"Orchestrator router: action={result['action']}")
    return result

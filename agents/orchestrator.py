"""FSM-based orchestrator — replaces the old coordinator + participant."""

import json
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

from models.state import JobAIdState, OrchestratorStage
from guardrails.bounded_autonomy import BoundedAutonomy
from config.settings import settings
from config.prompts import ORCHESTRATOR_ROUTER_SYSTEM
from utils import debug

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
    if stage == "parsing":
        return bool(state.get("resume_info"))
    if stage == "discovery":
        return bool(state.get("scored_jobs"))
    if stage == "market_intel":
        return bool(state.get("skill_gaps"))
    if stage == "pitching":
        return bool(state.get("final_pitch"))
    if stage == "summarizing":
        return bool(state.get("summary"))
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

    resume_info = state.get("resume_info")
    if resume_info:
        name = (resume_info.get("contact_info") or {}).get("name", "Unknown")
        skills = (resume_info.get("skills") or {}).get("technical", [])
        parts.append(f"Resume parsed: {name}, skills: {', '.join(skills[:8])}")
    else:
        parts.append("Resume: not yet parsed")

    scored_jobs = state.get("scored_jobs") or []
    if scored_jobs:
        parts.append(f"Scored jobs ({len(scored_jobs)} found):")
        for i, job in enumerate(scored_jobs):
            title = job.get("title", "Unknown")
            company = job.get("company", "Unknown")
            score = job.get("score", "?")
            parts.append(f"  [{i}] {title} at {company} (score: {score})")
    else:
        parts.append("Scored jobs: none yet")

    if state.get("skill_gaps"):
        parts.append("Market intelligence: available")
    else:
        parts.append("Market intelligence: not yet run")

    if state.get("final_pitch"):
        parts.append("Cover letter/pitch: generated")
    else:
        parts.append("Cover letter/pitch: not yet generated")

    if state.get("summary"):
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

    Returns dict with: action, response_text, parameters.
    """
    state_summary = _build_state_summary(state)
    system_prompt = ORCHESTRATOR_ROUTER_SYSTEM.format(state_summary=state_summary)

    llm = ChatOpenAI(
        model=settings.default_model,
        api_key=settings.openai_api_key,
        temperature=0.1,
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message),
    ]

    debug(f"Orchestrator router: interpreting '{user_message}'")
    response = llm.invoke(messages)

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

    debug(f"Orchestrator router: action={result['action']}")
    return result

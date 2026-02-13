"""LangGraph node wrappers with error boundaries."""

from typing import Dict, Any
from models.state import JobAIdState
from agents.orchestrator import handle_stage_error
from utils import debug


def _safe_run(stage: str, fn, state: JobAIdState) -> Dict[str, Any]:
    """Run an agent function with error boundary."""
    try:
        return fn(state)
    except Exception as exc:
        debug(f"Node error in {stage}: {exc}")
        error_update = handle_stage_error(state, stage, str(exc))
        messages = list(state.get("messages") or [])
        messages.append({"role": "assistant", "content": f"[{stage}] Error: {exc}"})
        error_update["messages"] = messages
        return error_update


def resume_parser_node(state: JobAIdState) -> Dict[str, Any]:
    from agents.resume_parser import resume_parser
    debug("Entering resume_parser_node")
    result = _safe_run("parsing", resume_parser, state)
    return result


def job_discovery_node(state: JobAIdState) -> Dict[str, Any]:
    from agents.job_discovery import job_discovery
    debug("Entering job_discovery_node")
    result = _safe_run("discovery", job_discovery, state)
    return result


def market_intelligence_node(state: JobAIdState) -> Dict[str, Any]:
    from agents.market_intelligence import market_intelligence
    debug("Entering market_intelligence_node")
    result = _safe_run("market_intel", market_intelligence, state)
    return result


def pitch_generator_node(state: JobAIdState) -> Dict[str, Any]:
    from agents.pitch_generator import pitch_generator
    debug("Entering pitch_generator_node")
    result = _safe_run("pitching", pitch_generator, state)
    return result


def summarizer_node(state: JobAIdState) -> Dict[str, Any]:
    from agents.summarizer import summarizer
    debug("Entering summarizer_node")
    result = _safe_run("summarizing", summarizer, state)
    return result


def orchestrator_node(state: JobAIdState) -> Dict[str, Any]:
    from agents.orchestrator import determine_next_stage
    return determine_next_stage(state)


def review_node(state: JobAIdState) -> Dict[str, Any]:
    """HITL review checkpoint — returns state unchanged (approval comes via API/CLI)."""
    current = state.get("current_stage", "")
    debug(f"Review node: awaiting approval at {current}")
    return {}

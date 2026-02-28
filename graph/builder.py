"""LangGraph StateGraph construction for JobAId."""

from langgraph.graph import StateGraph, START, END
from models.state import JobAIdState
from graph.nodes import (
    orchestrator_node,
    resume_parser_node,
    job_discovery_node,
    market_intelligence_node,
    pitch_generator_node,
    summarizer_node,
    review_node,
)


def _route_from_orchestrator(state: JobAIdState) -> str:
    """Conditional edge: route from orchestrator to the appropriate agent node."""
    stage = state.get("current_stage", "complete")
    mapping = {
        "parsing": "resume_parser",
        "parsing_review": "review",
        "discovery": "job_discovery",
        "discovery_review": "review",
        "market_intel": "market_intelligence",
        "pitching": "pitch_generator",
        "pitch_review": "review",
        "summarizing": "summarizer",
        "complete": "end",
        "error": "end",
    }
    return mapping.get(stage, "end")


def build_graph() -> StateGraph:
    """Build and compile the JobAId LangGraph state machine."""
    builder = StateGraph(JobAIdState)

    # Add nodes
    builder.add_node("orchestrator", orchestrator_node)
    builder.add_node("resume_parser", resume_parser_node)
    builder.add_node("job_discovery", job_discovery_node)
    builder.add_node("market_intelligence", market_intelligence_node)
    builder.add_node("pitch_generator", pitch_generator_node)
    builder.add_node("summarizer", summarizer_node)
    builder.add_node("review", review_node)

    # Entry point
    builder.add_edge(START, "orchestrator")

    # Orchestrator routes to the correct agent
    builder.add_conditional_edges(
        "orchestrator",
        _route_from_orchestrator,
        {
            "resume_parser": "resume_parser",
            "job_discovery": "job_discovery",
            "market_intelligence": "market_intelligence",
            "pitch_generator": "pitch_generator",
            "summarizer": "summarizer",
            "review": "review",
            "end": END,
        },
    )

    # Each agent node loops back to orchestrator for next routing decision
    builder.add_edge("resume_parser", "orchestrator")
    builder.add_edge("job_discovery", "orchestrator")
    builder.add_edge("market_intelligence", "orchestrator")
    builder.add_edge("pitch_generator", "orchestrator")
    builder.add_edge("summarizer", "orchestrator")
    builder.add_edge("review", "orchestrator")

    return builder.compile()

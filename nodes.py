# nodes.py
from typing import Literal, Dict, Any
from state import State
from agents.coordinator import coordinator
from agents.participant import participant
from agents.summarizer import summarizer


def human_node(state: State) -> dict:
    """Prompt user for input and (re)start a volley and reset the pipeline."""
    user_input = input("\nYou: ").strip()
    human_message = {"role": "user", "content": f"You: {user_input}"}

    messages = state.get("messages", []).copy()
    messages.append(human_message)

    # (Re)start a volley and reset stage to the beginning of the pipeline
    volley = int(state.get("volley_msg_left", 0))
    if volley <= 0:
        volley = 5

    # Reset pipeline so each human turn can run resume->... again
    return {"messages": messages, "volley_msg_left": volley, "stage_idx": 0}


def check_exit_condition(state: State) -> Literal["summarizer", "coordinator"]:
    """If user typed 'exit' or volley ended, go summarizer; else coordinator."""
    msgs = state.get("messages", [])
    if msgs and "exit" in msgs[-1].get("content", "").lower():
        return "summarizer"
    if int(state.get("volley_msg_left", 0)) <= 0:
        return "summarizer"
    return "coordinator"


def coordinator_routing(state: State) -> Literal["participant", "human"]:
    # """
    # Continue agent loop while there’s volley; otherwise go back to human.
    # Also respect when an agent explicitly handed control back to human.
    # """
    # if state.get("next_agent") == "human":
    #     return "human"
    # return "participant" if int(state.get("volley_msg_left", 0)) > 0 else "human"

    """
    Decide whether to continue the participant pipeline or go back to human.
    """
    # After resume_parser → job_search → relevance_scorer → pitch_generator
    # the participant sets `next_agent` accordingly.

    # next_agent = getattr(state, "next_agent", None)
    next_agent = state.get("next_agent")
    print(f"[DEBUG] Coordinator routing: next_agent={next_agent}")

    # If the pipeline has another participant step, continue
    if next_agent in ["resume_parser", "job_search", "relevance_scorer", "pitch_generator"]:
        return "participant"

    # If the pipeline finished its last step (pitch_generator done), return to human
    if next_agent == "human" or next_agent is None:
        return "human"

    # Only return summarizer if explicitly told (like user exit)
    if next_agent == "summarizer":
        return "summarizer"

    # Default fallback
    return "human"


def _merge_non_message_fields(result: Dict[str, Any]) -> Dict[str, Any]:
    """Preserve any non-message outputs from agents in the state."""
    return {k: v for k, v in (result or {}).items() if k != "messages"}


def participant_node(state: State) -> dict:
    """
    Call the selected agent, print its messages, advance stage, and
    reduce volley. If the agent says 'human' next, end the volley.
    """
    next_agent = state.get("next_agent", "resume_parser")

    # If pipeline finished, just return state
    if next_agent is None:
        return state

    # # If pipeline finished and next_agent is human, call human_node directly
    # if next_agent == "human":
    #     return human_node(state)

    # Otherwise, delegate to the participant pipeline
    result = participant(next_agent, state)

    if result and "messages" in result:
        messages = state.get("messages", []).copy()
        for msg in result["messages"]:
            print(msg.get("content", ""))
            messages.append(msg)

        # advance stage index (no clamping)
        old_idx = int(state.get("stage_idx", 0))
        stage_idx = old_idx + 1
        print(f"    [DEBUG] [PARTICIPANT] stage_idx: {old_idx} -> {stage_idx}")

        # spend one volley
        volley = max(0, int(state.get("volley_msg_left", 0)) - 1)

        # If the agent finished the pipeline and handed control back to human,
        # force volley to 0 so check_exit_condition will end with a summary.
        if result.get("next_agent") == "human":
            volley = 0

        # merge any extra keys from result (except messages)
        merged = _merge_non_message_fields(result)

        return {
            "messages": messages,
            "volley_msg_left": volley,
            "stage_idx": stage_idx,
            **merged,
        }

    return {}


def summarizer_node(state: State) -> dict:
    """Generate and print final summary."""
    print("\n=== ENDING ===\n")
    print(summarizer(state))
    print("\nThank you!")
    return {}

from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

def summarizer(state) -> str:
    """
    Generate summary when conversation ends (same return format as sample).
    """

    messages = state.get("messages", [])
    print("[DEBUG] Summarizer received messages:")
    for i, m in enumerate(messages):
        print(f"  [{i}] {m}")
    if not messages:
        print("[DEBUG] No messages to summarize.")
        return "No conversation to summarize."

    conversation_text = "\n".join(m.get("content", "") for m in messages if isinstance(m, dict))
    print("[DEBUG] Summarizer conversation_text:")
    print(conversation_text)

    if not conversation_text.strip():
        print("[DEBUG] No conversation content to summarize.")
        return "No conversation content to summarize."

    system_prompt = """You are the observer of a Job Search multi-agent run.

Summarize crisply:
1) What each agent accomplished (Resume Parser, Job Search, Relevance Scorer, Pitch Generator).
2) Key data passed between agents (skills, listings, scores, final pitch).
3) Final recommendation / next action for the user.

Keep it short, structured, and readable.
"""

    user_prompt = f"""Transcript / log:

{conversation_text}

Please summarize the outcome for the end-of-run report."""

    try:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=1)
        response = llm.invoke([SystemMessage(content=system_prompt),
                               HumanMessage(content=user_prompt)])
        text = response.content if isinstance(response.content, str) else str(response.content)

        # optional: expose top match/pitch if available
        top_line = ""
        scored = state.get("scored_jobs") or []
        if scored:
            top = scored[0]
            j = top.get("job", {})
            top_line = f"\n\nTop match: {j.get('title','(N/A)')} @ {j.get('company','(N/A)')} ({top.get('score','?')}/100)"
        pitch_line = f"\n\n=== SAMPLE PITCH ===\n{state.get('final_pitch','')}" if state.get("final_pitch") else ""

        return f"=== JOB CONNECT SUMMARY ===\n\n{text.strip()}{top_line}{pitch_line}"

    except Exception:
        # Fallback similar to your sample style
        return (f"=== JOB CONNECT SUMMARY ===\n\n"
                f"Total messages: {len(messages)}\n\n"
                f"Unable to generate detailed summary at this time.")

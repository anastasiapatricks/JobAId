"""CLI entry point for JobAId."""

import sys
import os
import uuid

# Ensure project root is on sys.path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from agents.resume_parser import load_resume_from_file
from agents.orchestrator import reset_autonomy
from graph.builder import build_graph
from utils import debug


def get_user_input() -> tuple[str, str] | None:
    """Ask user for resume file path and job query.  Returns (resume_text, job_query) or None."""
    print("\n=== JobAId — AI-Powered Job Search Assistant ===")
    resume_path = input("Enter path to your resume file (or 'exit' to quit): ").strip()
    if resume_path.lower() == "exit":
        return None

    try:
        resume_text = load_resume_from_file(resume_path)
    except FileNotFoundError:
        print(f"[Error] File '{resume_path}' not found. Try again.\n")
        return get_user_input()

    job_query = input("Enter job search keywords (or 'exit' to quit): ").strip()
    if job_query.lower() == "exit":
        return None

    location = input("Preferred location (press Enter to skip): ").strip() or None

    return resume_text, job_query, location


def print_results(state: dict):
    """Print final pipeline results."""
    print("\n" + "=" * 60)
    print("  JobAId Results")
    print("=" * 60)

    # Resume summary
    info = state.get("resume_info")
    if info:
        contact = info.get("contact_info", {})
        name = contact.get("name", "Candidate")
        skills = info.get("skills", {})
        tech = skills.get("technical", []) if isinstance(skills, dict) else []
        print(f"\n--- Resume: {name} ---")
        if tech:
            print(f"  Skills: {', '.join(tech[:10])}")
        yoe = info.get("years_of_experience")
        if yoe:
            print(f"  Experience: {yoe} years")

    # Top job matches
    scored = state.get("scored_jobs") or []
    if scored:
        print("\n--- Top Job Matches ---")
        for i, j in enumerate(scored[:5], 1):
            print(f"  {i}. {j.get('title', '?')} @ {j.get('company', '?')} — {j.get('score', '?')}/100")
            if j.get("explanation"):
                print(f"     {j['explanation']}")

    # Skill gaps
    gaps = state.get("skill_gaps") or []
    if gaps:
        print("\n--- Skill Gaps ---")
        for g in gaps[:5]:
            print(f"  - {g.get('skill', '?')} ({g.get('importance', 'medium')})")

    # Upskilling roadmap
    roadmap = state.get("upskilling_roadmap") or []
    if roadmap:
        print("\n--- Upskilling Roadmap ---")
        for item in roadmap[:5]:
            courses = item.get("recommended_courses", [])
            print(f"  - {item.get('skill', '?')}: {', '.join(courses[:2]) if courses else 'self-study'}")

    # Salary insights
    salary = state.get("salary_insights")
    if salary and isinstance(salary, dict):
        currency = salary.get("currency", "SGD")
        mn = salary.get("min_salary")
        mx = salary.get("max_salary")
        if mn and mx:
            print(f"\n--- Salary Range ---")
            print(f"  {currency} {mn:,.0f} – {mx:,.0f}")

    # Cover letter
    pitch = state.get("final_pitch")
    if pitch:
        print(f"\n--- Cover Letter ---")
        print(pitch)

    # Summary
    summary = state.get("summary")
    if summary:
        print(f"\n--- Summary ---")
        print(summary)

    # Decision log (debug)
    log = state.get("decision_log") or []
    if log and os.getenv("DEBUG", "false").lower() == "true":
        print(f"\n--- Decision Log ({len(log)} entries) ---")
        for entry in log:
            print(f"  [{entry.get('stage')}] {entry.get('action')}: {entry.get('reasoning')}")

    # Errors / fallbacks
    errors = state.get("errors") or []
    if errors:
        print(f"\n--- Warnings ({len(errors)}) ---")
        for e in errors:
            print(f"  [{e.get('stage')}] {e.get('error')}")

    print("\n" + "=" * 60)


def main():
    load_dotenv(override=True)

    graph = build_graph()

    while True:
        user_input = get_user_input()
        if not user_input:
            print("\nGoodbye!")
            break

        resume_text, job_query, location = user_input
        print(f"\n[INPUT] Resume loaded ({len(resume_text)} chars), query: '{job_query}'")
        print("[INFO] Running JobAId pipeline...\n")

        # Reset orchestrator state for this run
        reset_autonomy()

        initial_state = {
            "session_id": str(uuid.uuid4()),
            "messages": [],
            "current_stage": "intake",
            "stage_history": [],
            "iteration_count": 0,
            "max_iterations": 20,
            "requires_human_approval": False,
            "resume_text": resume_text,
            "job_query": job_query,
            "location_preference": location,
            "decision_log": [],
            "errors": [],
            "fallback_used": [],
        }

        try:
            final_state = graph.invoke(initial_state, config={"recursion_limit": 50})
            print_results(final_state)
        except KeyboardInterrupt:
            print("\n\nInterrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n[ERROR] Pipeline failed: {e}")

        again = input("\nProcess another resume? (y/n): ").strip().lower()
        if again != "y":
            print("\nGoodbye!")
            break


if __name__ == "__main__":
    main()

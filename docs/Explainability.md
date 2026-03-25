# Explainability Drawer — How Values Are Derived

This document explains how each value displayed in the explainability drawer is computed. The drawer is accessible via the "Explainability" toolbar button (psychology icon) and provides transparency into every agent's decision-making process.

---

## Summary Bar

| Metric | How it's derived |
|--------|------------------|
| **Agents ran** | Count of agents that have returned results in the current session |
| **Avg confidence** | Average of each agent's confidence score (see table below), displayed as a percentage |
| **Warnings** | Total count of flagged issues across all agents (e.g., low grounding, fallback used, unverified claims) |

---

## Per-Agent Confidence

Each agent calculates its confidence differently, based on what it does:

| Agent | How confidence is derived |
|-------|--------------------------|
| **Resume Parser** | How completely the LLM extracted the resume. If name, skills, experience, and education are all found, confidence is high. Missing fields lower it. |
| **Job Discovery** | The top job's match score divided by 100. If the best job scored 82/100, confidence = 0.82. |
| **Market Intelligence** | Average of how many recommended courses could be verified against real source data (Tavily search results or ChromaDB seed data). If 3 out of 4 courses traced back to a real source, confidence is approximately 0.75. |
| **Pitch Generator** | Based on grounding verification — checks whether the cover letter's claims (skills mentioned, company name, experience) actually match what's in the resume and job listing. More verified claims = higher confidence. |
| **Summarizer** | Checks if the final summary references real data from the session — does it mention the candidate's name? The top company? Identified skill gaps? Each reference found adds to the score. |

The confidence ring is colour-coded: green (>= 70%), amber (>= 40%), red (< 40%).

---

## Grounding Score

The grounding bar measures how much of the agent's output is backed by actual data versus potentially fabricated:

| Agent | How grounding is calculated |
|-------|----------------------------|
| **Job Discovery** | Ratio of candidate skills that overlap with job keywords. If the job lists 10 keywords and 6 match your skills, grounding = 0.6. |
| **Market Intelligence** | What fraction of recommended courses can be traced to a real source (Tavily result or seed data entry). Unverifiable courses get flagged. |
| **Pitch Generator** | The cover letter is scanned for claims. Each claim is checked: does the skill exist in the resume? Does the company name match? Are years-of-experience claims accurate? Verified claims / total claims = grounding score. |
| **Summarizer** | Checks if the summary references the candidate's actual name, top-matched company, and identified skill gaps rather than being generic boilerplate. |

The grounding bar is colour-coded the same way as confidence: green (>= 0.7), amber (>= 0.4), red (< 0.4).

---

## Key Factors

The "Key Factors" section renders differently depending on which agent produced the result:

### SHAP Bar Chart (Job Discovery)

For the top-matched job, the system asks: "how much does each of your skills contribute to the match?"

It computes this using Shapley values from game theory — for every possible combination of your skills, it calculates the match score with and without each skill, then measures each skill's marginal contribution. The bar chart shows the top 8 skills ranked by contribution. A longer bar means that skill matters more for this particular job match.

If there is zero overlap between your skills and the job's listed keywords, the system displays a note explaining that the score came from the LLM's semantic assessment instead of keyword matching.

### Skill Gap Explanations (Market Intelligence)

For each skill gap identified, the agent traces *why* it was flagged. For example: "Kubernetes is required by 2 of your top job matches but is not in your current profile."

This comes from comparing your resume skills against the keywords extracted from the jobs you matched with. Each gap is shown with its explanation so you can understand which jobs need that skill.

### Match Analysis (Pitch Generator)

The LLM's analysis of how the candidate's profile aligns with the job requirements — strengths, relevant experience, and transferable skills. These are the key findings from the match analysis step (step 2 of the 4-step cover letter generation chain), displayed as key-value pairs.

### Generic Key-Values (Resume Parser / Orchestrator)

For agents without specialised attribution types, the drawer shows what data the agent worked with. For example, the orchestrator shows the action it chose and the parameters it used for routing.

---

## Sources Consulted

Each agent records which data sources it actually queried during execution:

| Source | Meaning |
|--------|---------|
| **llm** | Called OpenAI (GPT-4o-mini) for generation or analysis |
| **rag** / **chromadb** | Searched the ChromaDB vector database (courses, trends, cover letter samples, or jobs) |
| **tavily** | Performed a real-time web search via the Tavily API |
| **adzuna** | Queried the Adzuna job board API for live job listings |

This tells you whether a result came from just the LLM's training data or was augmented with real, current external data.

---

## Warnings

Agents flag concerns as they encounter them during execution. Examples include:

| Warning | Meaning |
|---------|---------|
| Fallback scoring used | The normal scoring method failed, so a simpler backup method was used |
| Low grounding score | The output doesn't reference much real data — may be more generic than expected |
| Unverified claim | A claim in the cover letter couldn't be traced back to the resume or job listing |
| Experience mismatch | The cover letter states a different number of years than the resume (e.g., letter says "5 years" but resume shows 3) |
| Query reformulation | The original job search query was modified to get better results |

---

## Decision Timeline

Every time the orchestrator routes a user message, it records three things:

1. **Stage** — which pipeline stage it was in (e.g., discovery, market_intel, pitching)
2. **Action** — what it decided to do:
   - **Advance** (green dot) — move forward to the next stage
   - **Retry** (amber dot) — try the current stage again
   - **Skip** (red dot) — skip the current stage and move on
   - **Force complete** (gray dot) — end the pipeline
3. **Reasoning** — the orchestrator's explanation for why it made that routing decision

The timeline is displayed chronologically, providing a full audit trail of how the pipeline was orchestrated for the current session.

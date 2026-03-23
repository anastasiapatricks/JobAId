# Explainable & Responsible AI (XAI) Module

## What This Module Does

Every agent in JobAId now produces an `explainability_trace` alongside its normal output. This trace answers three questions for every decision the system makes:

1. **What did the agent decide?** (confidence score, action taken)
2. **Why?** (feature attributions, reasoning string, grounding verification)
3. **Can we trust it?** (source verification, fairness audit, grounding score)

The module implements two XAI techniques taught in SWE5008G Module 1 (SHAP and LIME), plus AIF360-inspired fairness checks, all in pure Python with no additional dependencies.

---

## Architecture

```
xai/
  __init__.py          Re-exports all public APIs
  trace.py             ExplainabilityTrace dataclass + create_trace() factory
  explainers.py        SHAP-like and LIME-like skill attribution (with enrichment)
  fairness.py          Statistical Parity + Equal Opportunity checks
  grounding.py         Cover letter claim verification
```

Every agent appends its trace to the result dict under the key `explainability_trace`. Because `ResultEntry` uses `model_config = {"extra": "allow"}`, these new fields flow through the API to the frontend without schema changes.

---

## How to Observe XAI Output — Step by Step

### Step 1: Start the servers

```bash
cd ~/Documents/JobAId

# Start the backend (FastAPI)
.venv/bin/python3 -m uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload

# In a separate terminal, start the frontend (Angular)
cd frontend && npx ng serve --host 0.0.0.0 --port 4200
```

- Frontend: http://localhost:4200
- Backend API: http://localhost:8000
- Swagger docs: http://localhost:8000/docs

### Step 2: Use the app normally via the frontend

1. Open http://localhost:4200 in your browser.
2. Upload or paste a resume.
3. Wait for the parsing to complete (you'll see a confidence score and skill list).
4. Type a job search query (e.g., "Find cybersecurity jobs in Singapore").
5. The system returns ranked jobs with scores.
6. Pick a job to get a cover letter (e.g., "I'm interested in the Google one").
7. The system auto-runs market intelligence then generates the cover letter.

All XAI computation happens behind the scenes during each step. The XAI output is attached to every agent's result.

### Step 3: Inspect XAI output via the API

While the app is running, open a terminal and call the results endpoint. First, find your session ID:

```bash
curl -s http://localhost:8000/api/sessions | python3 -m json.tool
```

Then fetch results for that session:

```bash
curl -s http://localhost:8000/api/sessions/{SESSION_ID}/results | python3 -m json.tool
```

Each entry in the `results` array now contains XAI fields. Here is what to look for in each agent's output:

#### After resume parsing (`"action": "parsing"`)

```jsonc
{
  "action": "parsing",
  "explainability_trace": {
    "agent_name": "resume_parser",
    "prompt_version": "1.0.0",
    "confidence": 0.9,
    "reasoning": "Extracted via llm; 23 skills, 5 yrs experience",
    "feature_attributions": {
      "contact_info": 1.0,   // 1.0 = section present, 0.0 = missing
      "skills": 1.0,
      "experience": 1.0,
      "education": 1.0
    },
    "sources_consulted": ["llm"],
    "warnings": ["Missing fields: LinkedIn profile, GitHub profile"]
  }
}
```

**What to observe:** The `feature_attributions` map shows which resume sections were successfully extracted (1.0) vs missing (0.0). The `confidence` is the LLM's self-assessed parsing quality. If the LLM fails entirely, `sources_consulted` changes to `["regex_fallback"]`.

#### After job search (`"action": "discovery"`)

```jsonc
{
  "action": "discovery",
  "explainability_trace": {
    "agent_name": "job_discovery",
    "prompt_version": "1.0.0",
    "confidence": 0.50,
    "reasoning": "Ranked 10 jobs from 15 candidates; source=adzuna",
    "feature_attributions": {
      "top_job_shap": { "incident response": 0.5, "cybersecurity": 0.5 }
    },
    "sources_consulted": ["adzuna", "chromadb"]
  },

  "shap_attributions": {
    "Incident Response Consultant @ Google": {
      "incident response": 0.5000,
      "cybersecurity": 0.5000,
      "_meta": { "method": "keywords", "keyword_count": 2, "overlap_count": 2 }
    },
    "Cyber Security Lead @ Certis": {
      "incident response": 0.2000,
      "cybersecurity": 0.2000,
      "security operations": 0.2000,
      "_meta": { "method": "keywords", "keyword_count": 5, "overlap_count": 3 }
    }
  },

  "lime_explanations": [
    {
      "skill": "incident response",
      "impact": 0.5000,
      "direction": "positive",
      "baseline_score": 1.0000,
      "perturbed_score": 0.5000,
      "_meta": { "method": "keywords", "keyword_count": 2, "overlap_count": 2 }
    },
    {
      "skill": "cybersecurity",
      "impact": 0.5000,
      "direction": "positive",
      "baseline_score": 1.0000,
      "perturbed_score": 0.5000
    }
  ],

  "fairness_audit": {
    "statistical_parity": {
      "test": "statistical_parity",
      "passed": true,
      "local_mean": 35.0,
      "remote_mean": 32.5,
      "gap": 2.5,
      "detail": "Local jobs (4): mean 35.0, Remote jobs (6): mean 32.5, gap 2.5"
    },
    "equal_opportunity": {
      "test": "equal_opportunity",
      "passed": true,
      "local_rate": 0.25,
      "remote_rate": 0.1667,
      "gap": 0.0833,
      "threshold": 70
    }
  }
}
```

**What to observe:**

- **SHAP (`shap_attributions`)**: For each of the top 5 jobs, shows which candidate skills contributed to the match score and by how much. Read it as: "Your 'incident response' skill contributed +0.50 (50%) to your match score for the Google role." Skills with 0.0 had no effect.
- **LIME (`lime_explanations`)**: For the top job, shows what happens when each skill is removed one at a time. Read it as: "If you removed 'incident response' from your profile, your match score would drop from 1.0 to 0.5."
- **Fairness audit**: Checks whether job scoring is biased by location. `passed: true` means the gap between local and remote mean scores is within 10 points (Statistical Parity) and selection rates are within 20% (Equal Opportunity).
- **`_meta`**: Every SHAP/LIME result includes a `_meta` object showing the `method` used (`"keywords"` or `"keywords+description"` — see [Keyword Enrichment](#keyword-enrichment-solving-the-zero-overlap-problem) below), how many keywords were matched, and how many overlapped.

#### After market analysis (`"action": "market_intel"`)

```jsonc
{
  "action": "market_intel",
  "explainability_trace": {
    "agent_name": "market_intelligence",
    "prompt_version": "1.1.0",
    "confidence": 0.5,
    "reasoning": "5 gaps, 5 courses, 5/10 grounded",
    "grounding_score": 0.5,
    "feature_attributions": {
      "skill_gaps_with_explanations": [
        {
          "skill": "Java",
          "explanation": "'Java' is required by 2 of your top job matches (Java Tech Lead, Java Backend Developer) but is not in your current profile."
        }
      ]
    },
    "sources_consulted": ["tavily_courses", "tavily_trends", "seed_salary_data", "llm"]
  }
}
```

**What to observe:** The `feature_attributions.skill_gaps_with_explanations` traces each skill gap back to the specific jobs that demand it. The `grounding_score` shows what fraction of recommended courses can be traced back to the Tavily/RAG search results (vs LLM-hallucinated suggestions).

#### After cover letter generation (`"action": "pitching"`)

```jsonc
{
  "action": "pitching",
  "explainability_trace": {
    "agent_name": "pitch_generator",
    "prompt_version": "1.0.0",
    "confidence": 1.0,
    "reasoning": "4-step chain for Java Tech Lead @ Julius Baer; 2 claims grounded",
    "grounding_score": 1.0,
    "sources_consulted": ["company_research", "match_analysis", "llm_draft", "llm_review"]
  },
  "grounding_verification": {
    "grounding_score": 1.0,
    "verified_claims": [
      "Company 'Julius Baer' correctly referenced",
      "Job title 'Java Tech Lead' correctly referenced"
    ],
    "unverified_claims": [],
    "warnings": []
  }
}
```

**What to observe:** The `grounding_verification` checks every factual claim in the cover letter against the resume and job data. `verified_claims` lists what checked out. `unverified_claims` flags anything the LLM wrote that cannot be traced to the source data. `warnings` highlights specific problems (e.g., "Claims 10 years but resume shows 2").

### Step 4: Run the XAI tests independently

The XAI module can be tested without the server or any LLM calls:

```bash
cd ~/Documents/JobAId
PYTHONPATH=. python3 -m pytest tests/test_xai.py -v
```

This runs 22 tests covering all XAI components in isolation.

### Step 5: Experiment in the Python REPL

```bash
cd ~/Documents/JobAId
PYTHONPATH=. .venv/bin/python3
```

```python
from xai.explainers import shap_skill_attribution, lime_job_explanation

# SHAP: Which of my skills matter most for this job?
shap = shap_skill_attribution(
    candidate_skills=["python", "incident response", "splunk", "volatility"],
    job_keywords=["python", "incident response", "splunk", "kubernetes"],
)
for skill, value in shap.items():
    if skill != "_meta":
        print(f"  {skill}: {value:+.4f}")
# Output:
#   python: +0.2500
#   incident response: +0.2500
#   splunk: +0.2500
#   volatility: +0.0000   (not in job keywords, contributes nothing)

# LIME: What happens when I remove each skill?
lime = lime_job_explanation(
    candidate_skills=["python", "incident response", "splunk", "volatility"],
    job_keywords=["python", "incident response", "splunk", "kubernetes"],
    top_n=3,
)
for item in lime:
    if "_meta" not in item:
        print(f"  {item['skill']}: removing drops {item['baseline_score']:.2f} -> {item['perturbed_score']:.2f}")
# Output:
#   python: removing drops 0.75 -> 0.50
#   incident response: removing drops 0.75 -> 0.50
#   splunk: removing drops 0.75 -> 0.50

# SHAP with description fallback (zero keyword overlap):
shap2 = shap_skill_attribution(
    candidate_skills=["python", "docker", "kubernetes"],
    job_keywords=["java", "spring boot"],  # no overlap with candidate
    job_description="We need someone with python and docker experience for our platform team",
)
print(shap2["_meta"])
# {'method': 'keywords+description', 'keyword_count': 4, 'overlap_count': 2}
# Now python and docker show non-zero values because the description was scanned.

# Fairness check:
from xai.fairness import statistical_parity_check
jobs = [
    {"score": 90, "location": "Singapore"},
    {"score": 85, "location": "Singapore"},
    {"score": 50, "location": "Remote"},
    {"score": 45, "location": "Remote"},
]
result = statistical_parity_check(jobs, "Singapore")
print(f"Passed: {result['passed']}, Gap: {result['gap']}")
# Passed: False, Gap: 40.0  (Singapore jobs scored way higher — bias detected)

# Grounding check on a cover letter:
from xai.grounding import verify_pitch_grounding
grounding = verify_pitch_grounding(
    pitch_text="As a Python engineer with 5 years at Acme Corp, I'm excited about BigCo.",
    resume_info={
        "skills": {"technical": ["Python"], "soft": [], "certifications": []},
        "experience": [{"title": "Engineer", "company": "Acme Corp"}],
        "years_of_experience": 5,
    },
    job_info={"title": "Software Engineer", "company": "BigCo"},
)
print(f"Grounding: {grounding['grounding_score']:.0%}")
print(f"Verified: {grounding['verified_claims']}")
print(f"Warnings: {grounding['warnings']}")
```

---

## Keyword Enrichment: Solving the Zero-Overlap Problem

### The problem

The SHAP and LIME explainers operate on set-intersection between the candidate's skills and the job's keywords. This works well when there is overlap — but in practice, many job listings (especially from the Adzuna API) have sparse, generic keywords like `["cybersecurity", "incident response"]`, while the candidate's parsed skills are tool-specific names like `["Volatility", "WinDbg", "IDA Pro", "Ghidra"]`.

When there is zero overlap between these two sets, every Shapley value is 0.0 and every LIME perturbation shows zero impact. Technically correct ("none of your parsed tool skills match this job's keywords"), but completely useless as an explanation.

### The solution: two-layer enrichment

We address this at two levels so that SHAP/LIME always has a meaningful skill-to-keyword mapping to explain.

#### Layer 1: Candidate-side domain term extraction (`job_discovery.py`)

The resume parser extracts specific tool names (Volatility, Splunk, Ghidra) as skills. But the resume's professional summary and experience descriptions also contain domain-level terms like "incident response", "malware analysis", "digital forensics", "threat hunting", "security operations" — these are exactly the terms that appear in job keywords.

Before running SHAP/LIME, the job discovery agent scans the candidate's `professional_summary` and `experience[].description` fields using the same `_extract_keywords_from_text()` function that Adzuna uses to tag jobs. Any domain terms found (e.g., "incident response") are added to the candidate's skill list alongside their tool-specific skills.

**Before enrichment:**
```
Candidate skills: [Python, Volatility, WinDbg, IDA Pro, Ghidra, Splunk, ...]
Job keywords:     [cybersecurity, incident response]
Overlap:          {} (empty — all SHAP values are 0.0)
```

**After enrichment:**
```
Candidate skills: [Python, Volatility, WinDbg, ..., cybersecurity, incident response,
                   malware analysis, digital forensics, threat hunting, ...]
Job keywords:     [cybersecurity, incident response]
Overlap:          {cybersecurity, incident response} — SHAP gives +0.50 each
```

This works because the same `_KNOWN_SKILLS` dictionary (defined in `tools/job_board_api.py`) is used both to tag jobs and to extract domain terms from the resume. The vocabulary is consistent.

#### Layer 2: Job-side description fallback (`xai/explainers.py`)

Even after candidate enrichment, some job descriptions mention specific tools in their free-text description that are not in the structured `keywords` field (because Adzuna's keyword extraction may have missed them). For example, a job description might say "Experience with Python and Docker required" but the keywords field only contains `["devops"]`.

When SHAP/LIME detects zero overlap between the (enriched) candidate skills and the job's keywords, it scans the job's title + description using `_extract_keywords_from_text()` and adds any additional terms to the keyword set.

Each SHAP/LIME result includes a `_meta` object that reports which method was used:

| `_meta.method` | Meaning |
|---|---|
| `"keywords"` | Structured keywords had overlap with candidate skills. No enrichment needed. |
| `"keywords+description"` | Structured keywords had no overlap. Job description was scanned for additional terms. |

This transparency means the user (or evaluator) always knows whether the explanation is based on structured data or a description scan.

### Why not always enrich?

We only enrich when there is zero overlap. If structured keywords already overlap with candidate skills, adding description terms would dilute the Shapley values by increasing the denominator (more keywords = each matching skill contributes a smaller fraction). The structured keywords are the authoritative signal when they work.

---

## Per-Agent XAI Breakdown

### Resume Parser

| Field | Value |
|---|---|
| **Technique** | Feature attribution (field completeness) |
| **Why this technique** | Parsing is a structured extraction task, not a ranking. There are no "competing features" to run SHAP on. Instead, we attribute confidence to the presence/absence of four key resume sections (contact info, skills, experience, education), each scored 0 or 1. This tells the user exactly which sections drove the confidence score and where to improve their resume. |
| **Trace fields** | `confidence` (LLM-assessed), `feature_attributions` (section completeness), `sources_consulted` ("llm" or "regex_fallback"), `warnings` (low confidence, missing fields) |

### Job Discovery

| Field | Value |
|---|---|
| **Techniques** | SHAP (Shapley values), LIME (perturbation), Fairness audit |
| **Why SHAP here** | Job matching is the core ranking decision. Users need to understand why Job A scored higher than Job B. SHAP computes the marginal contribution of each candidate skill to the match ratio for each of the top 5 jobs. It answers: "Your 'incident response' skill contributed 50% of your match score for the Google role." This is a natural fit because the skill-triage logic is a set-intersection (coalition game) which is exactly what Shapley values model. |
| **Why LIME here** | LIME complements SHAP by answering a different question for the top job: "If I didn't have 'incident response', my match score drops from 1.0 to 0.5." This remove-one-at-a-time perturbation is intuitive for users deciding which skills to prioritize on their resume. |
| **Why Fairness here** | Job scoring is the highest-risk decision for bias. If the system systematically scores local jobs higher than remote ones, that is location bias. We run Statistical Parity (are mean scores balanced across location groups?) and Equal Opportunity (are selection rates balanced above the 70-point threshold?) on every discovery run. These are the two fairness metrics taught in the AIF360 module. |
| **Enrichment** | Candidate skills are enriched with domain terms from the resume. Job keywords are enriched from the description if there is zero overlap. See [Keyword Enrichment](#keyword-enrichment-solving-the-zero-overlap-problem). |
| **Trace fields** | `confidence` (top job score / 100), `shap_attributions` (per job, with `_meta`), `lime_explanations` (top job, with `_meta`), `fairness_audit` (both checks), `sources_consulted` (adzuna/mock, chromadb) |

### Market Intelligence

| Field | Value |
|---|---|
| **Technique** | Source grounding verification (existing), unified trace (new) |
| **Why no SHAP/LIME** | This agent already had the richest XAI in the system: `_build_skill_gap_explanations()` traces each gap back to the specific jobs that demand it, and `_verify_sources()` cross-checks every course recommendation against RAG context. Adding SHAP on top would be redundant since the skill gap explanations already decompose the output by feature. Instead, we wrapped the existing XAI in the unified `ExplainabilityTrace` format so it is consistent with all other agents. |
| **Trace fields** | `confidence` (course grounding ratio), `grounding_score` (verified/total courses), `feature_attributions` (skill gaps with per-gap explanations), `sources_consulted` (tavily_courses, chromadb_courses, tavily_trends, seed_salary_data, llm), `warnings` (low grounding, validation issues) |

### Pitch Generator

| Field | Value |
|---|---|
| **Technique** | Grounding verification (claim-level) |
| **Why grounding, not SHAP** | Cover letters are free-text generation, not scoring. The risk is hallucination: the LLM might claim the candidate has 10 years of experience when the resume says 2. Grounding verification checks every factual claim (skills mentioned, company name, experience years, previous employers) against the actual resume and job data. This produces a `grounding_score` (0-1) and lists `verified_claims` vs `unverified_claims` with specific warnings. This is more useful than SHAP because the user needs to trust the letter's accuracy, not understand a numeric score. |
| **Trace fields** | `confidence` (grounding score), `grounding_verification` (verified/unverified claims, warnings), `feature_attributions` (match analysis from step 2), `sources_consulted` (company_research, match_analysis, llm_draft, llm_review) |

### Orchestrator

| Field | Value |
|---|---|
| **Technique** | Routing confidence + reasoning trace |
| **Why this technique** | The orchestrator makes a single classification decision (which agent to invoke). There are no features to decompose with SHAP. Instead, we log the routing confidence (0.9 for definite actions, 0.6 for chitchat fallback) and a reasoning string showing what the user said and how it was interpreted. This makes the intent-routing decision auditable. |
| **Trace fields** | `confidence` (routing certainty), `reasoning` (user message snippet + resolved action), `feature_attributions` (action, parameters), `sources_consulted` (conversation_history, state_summary) |

### Summarizer

| Field | Value |
|---|---|
| **Technique** | Grounding score (existing `check_grounding()`), unified trace |
| **Why grounding** | The summarizer's risk is the same as the pitch generator's: it might state things not present in the session data. The existing `check_grounding()` already computes a grounding score by checking whether key terms from the state appear in the summary. We wrap this in the unified trace format. |
| **Trace fields** | `confidence` (grounding score), `grounding_score` (same), `sources_consulted` (session_state, decision_log), `warnings` (low grounding) |

---

## Design Decisions

### Why pure Python instead of the `shap` and `lime` libraries?

1. **Zero new dependencies.** The project already has a large dependency tree (LangChain, ChromaDB, Tavily, etc.). Adding `shap` pulls in `numba`, `llvmlite`, and `matplotlib`. Adding `lime` pulls in `scikit-learn`. Neither is justified for a set-intersection scoring function.

2. **Exact Shapley values.** The `shap` library uses approximations (KernelSHAP, TreeSHAP) designed for models with thousands of features. Our "model" is a set-intersection with at most 12 features. We can compute exact Shapley values by enumerating all 2^12 = 4096 coalitions in under 1ms. An approximation would be less accurate and slower to import.

3. **Transparent implementation.** For an academic submission, showing a 30-line Shapley computation is more educational than calling `shap.Explainer(model).shap_values(X)` on a black-box wrapper.

### Why not AIF360?

Same reasoning. AIF360 is designed for tabular ML pipelines with training data. Our "model" is an LLM scoring rubric. Statistical Parity and Equal Opportunity are simple enough to implement in 40 lines of Python, and the implementation is easier to audit and explain in a report.

### Why a dataclass instead of Pydantic for `ExplainabilityTrace`?

The trace is internal data that flows through the system as a dict (via `to_dict()`). It never crosses an API boundary as a typed model. Using a lightweight dataclass avoids coupling the XAI module to Pydantic and keeps import time minimal. The `ResultEntry` Pydantic model accepts it as a dict through `extra="allow"`.

### Why additive-only integration?

Every agent change is an append to the result dict after the existing return statement. No existing logic was modified, no control flow was changed, no imports were removed. This means:

- All existing tests still pass (the collection errors are pre-existing missing dependencies).
- Any downstream consumer that doesn't read the new keys is completely unaffected.
- The XAI output can be toggled off by simply not reading the new keys.

---

## Prompt Versioning

Every agent's prompt now has a version constant in `config/prompts.py`:

| Agent | Constant | Version |
|---|---|---|
| Resume Parser | `RESUME_PARSER_PROMPT_VERSION` | 1.0.0 |
| Job Discovery | `JOB_DISCOVERY_PROMPT_VERSION` | 1.0.0 |
| Market Intelligence | `MARKET_INTELLIGENCE_PROMPT_VERSION` | 1.1.0 |
| Pitch Generator | `PITCH_GENERATOR_PROMPT_VERSION` | 1.0.0 |
| Orchestrator | `ORCHESTRATOR_PROMPT_VERSION` | 1.0.0 |
| Summarizer | `SUMMARIZER_PROMPT_VERSION` | 1.0.0 |

Each `explainability_trace` includes the `prompt_version` used to generate it. This enables:
- **A/B evaluation**: Compare outputs across prompt versions
- **Rollback**: If a prompt change degrades quality, the version pinpoints when
- **Audit trail**: Every LLM call is traceable to a specific prompt version via the MLSecOps log

---

## Test Coverage

```
tests/test_xai.py — 22 tests, 0 dependencies on LLM or API

TestExplainabilityTrace (4 tests)
  - Default creation, parameterized creation, dict serialization, field access

TestShapAttribution (5 tests)
  - Balanced skills, empty skills, empty keywords, single skill
  - Description fallback when no keyword overlap

TestLimeExplanation (4 tests)
  - Top impact ranking, no overlap (zero impact), full overlap (all positive)
  - Description fallback when no keyword overlap

TestFairnessAudit (6 tests)
  - Statistical parity: balanced, biased, empty jobs, no location
  - Equal opportunity: balanced, violated

TestPitchGrounding (3 tests)
  - Grounded pitch, ungrounded pitch (experience mismatch), empty pitch
```

Run with:

```bash
cd ~/Documents/JobAId
PYTHONPATH=. python3 -m pytest tests/test_xai.py -v
```

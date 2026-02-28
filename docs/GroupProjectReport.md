# JobAId — LLM-Powered Multi-Agent Job Search Assistant

**Project Title:** JobAId — Agentic AI Job Search Assistant\
**Team Number:** Team 31\
**Team Members:** Sanath, Anastasia, Hany, Vincent

---

## 1. Executive Summary

### 1.1 Project Objective and Scope

JobAId is a multi-agent AI system that assists job seekers by automating the end-to-end job search workflow: resume parsing, job discovery and ranking, market intelligence with upskilling recommendations, tailored cover letter generation, and grounded summarisation. The system demonstrates key competencies across all four course modules — agentic AI architecture, explainable and responsible AI practices, AI-specific cybersecurity, and MLSecOps/LLMSecOps pipeline design.

### 1.2 Key Highlights

- **5 specialised LLM-powered agents** coordinated by an FSM-based orchestrator using LangGraph
- **RAG (Retrieval-Augmented Generation)** with ChromaDB for courses, industry trends, and job semantic matching
- **Real external APIs** — Adzuna job board API, Tavily web search, Wikipedia REST API — with graceful fallbacks
- **Comprehensive guardrails** — prompt injection detection (7 patterns), PII de-biasing, output validation, bounded autonomy (iteration/retry/LLM-call limits)
- **Human-in-the-Loop (HITL)** review checkpoints at key pipeline stages
- **Three-tier architecture** — Angular 20 chat UI, FastAPI REST API with SSE streaming, CLI interface
- **Full MLSecOps pipeline** — Docker containerisation, GitHub Actions CI/CD, Terraform infrastructure-as-code, CloudWatch monitoring
- **92 automated tests** covering unit tests, integration tests, and AI security tests

### 1.3 Constraints and Assumptions

- The system uses OpenAI models (GPT-4o, GPT-4o-mini) via API; no model training or fine-tuning is performed
- Adzuna job listings are real but limited to the free-tier API (250 requests/day); mock data fallback is provided
- ChromaDB runs in-process (no external database server); data re-seeds on each startup from JSON seed files
- The system is designed for demo/educational purposes and is not production-hardened for high concurrency

---

## 2. System Overview

JobAId runs a pipeline of 5 specialised agents coordinated by an FSM-based orchestrator. The user interacts through a conversational chat interface where they upload a resume, ask questions, and receive structured results from each agent.

### 2.1 Agent Roles

| Agent | Responsibility |
|---|---|
| **Orchestrator** | FSM-based pipeline controller with named stages, conditional transitions, HITL review checkpoints, and bounded autonomy |
| **Resume Parser** | LLM-powered structured extraction (skills, experience, education), confidence assessment, PII de-biasing |
| **Job Discovery & Matching** | Adzuna API search, ChromaDB semantic matching, LLM-powered ranking with scoring rubric |
| **Market Intelligence** | Skill gap analysis, RAG-powered upskilling roadmap with course recommendations, salary benchmarks, industry trends |
| **Pitch Generator** | 4-step prompt chaining: company research (Wikipedia + Tavily) → match analysis → draft generation → quality review |
| **Summarizer** | Grounded explainability — feeds full session state to LLM, generates markdown report with decision log |

### 2.2 High-Level Workflow

```
User uploads resume
        │
        ▼
┌───────────────┐
│  ORCHESTRATOR  │ ◄── FSM router (LLM-powered intent classification)
└───────┬───────┘
        │
        ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│ RESUME PARSER │────►│ JOB DISCOVERY │────►│ MARKET INTEL  │────►│ PITCH GEN     │
│               │     │ & MATCHING    │     │               │     │               │
│ - LLM extract │     │ - Adzuna API  │     │ - Skill gaps  │     │ - Company     │
│ - PII de-bias │     │ - ChromaDB    │     │ - Upskilling  │     │   research    │
│ - Confidence  │     │ - LLM ranking │     │ - Salary/RAG  │     │ - Prompt chain│
└───────────────┘     └───────────────┘     └───────────────┘     └───────────────┘
        │                     │                     │                     │
        └─────────────────────┴─────────────────────┴─────────────────────┘
                                        │
                                        ▼
                              ┌───────────────┐
                              │  SUMMARIZER   │
                              │ - Full state  │
                              │ - Decision log│
                              │ - Grounding   │
                              └───────────────┘
```

**Pipeline flow:** `intake → parsing → [review] → discovery → [review] → market_intel → pitching → [review] → summarizing → complete`

Review stages (`parsing_review`, `discovery_review`, `pitch_review`) are optional HITL checkpoints where the user can approve, provide feedback, or request re-runs.

---

## 3. System Architecture

### 3.1 Logical Architecture

The system follows a **three-tier architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────┐
│                    PRESENTATION TIER                     │
│                                                         │
│  Angular 20 SPA          CLI Interface                  │
│  - Chat-based UI         - Terminal prompts             │
│  - SSE streaming         - Sequential pipeline          │
│  - Material Design 3                                    │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP / SSE
┌────────────────────▼────────────────────────────────────┐
│                    APPLICATION TIER                      │
│                                                         │
│  FastAPI REST API                                       │
│  ├── Routes: sessions, pipeline, resume, health         │
│  ├── Middleware: structured JSON logging, CORS          │
│  └── Dependencies: session store, graph singleton       │
│                                                         │
│  LangGraph State Machine                                │
│  ├── Orchestrator Node (FSM router)                     │
│  ├── Agent Nodes (5 specialised agents)                 │
│  └── Conditional edges (stage transitions)              │
│                                                         │
│  Guardrails Layer                                       │
│  ├── Input filter (prompt injection, length limits)     │
│  ├── Output filter (structure validation, grounding)    │
│  ├── Bounded autonomy (iteration/retry/LLM limits)     │
│  ├── Model router (task-based LLM selection)            │
│  └── PII sanitiser (de-biasing for fairness)            │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                    DATA / SERVICES TIER                  │
│                                                         │
│  ChromaDB (vector store)     OpenAI API (LLM + embed)   │
│  ├── courses collection      ├── gpt-4o (quality tasks) │
│  ├── industry_trends         ├── gpt-4o-mini (routing)  │
│  └── jobs (dynamic)          └── text-embedding-3-small │
│                                                         │
│  External APIs                                          │
│  ├── Adzuna (job listings)                              │
│  ├── Tavily (web search)                                │
│  └── Wikipedia (company research)                       │
└─────────────────────────────────────────────────────────┘
```

### 3.2 Physical Architecture and Deployment Strategy

The system is containerised and deployed to AWS using infrastructure-as-code:

```
┌──────────────────────────────────────────────┐
│              AWS EC2 (t3.small)               │
│                                              │
│  ┌──────────────────┐  ┌──────────────────┐  │
│  │  Frontend (nginx) │  │  Backend (Python) │  │
│  │  - Angular SPA    │  │  - FastAPI + uv   │  │
│  │  - Reverse proxy  │──│  - LangGraph      │  │
│  │    /api/* → :8000 │  │  - ChromaDB       │  │
│  │  - Port 80        │  │  - Port 8000      │  │
│  └──────────────────┘  └──────────────────┘  │
│                                              │
│  Docker Compose (awslogs driver)             │
│  IAM Instance Profile (ECR + CloudWatch)     │
└──────────────────┬───────────────────────────┘
                   │
    ┌──────────────┼──────────────┐
    ▼              ▼              ▼
┌────────┐  ┌──────────┐  ┌──────────────┐
│  ECR   │  │CloudWatch│  │ OpenAI / API │
│Backend │  │  Logs    │  │  Endpoints   │
│Frontend│  │Dashboard │  │              │
│ repos  │  │ Alarms   │  │              │
└────────┘  └──────────┘  └──────────────┘
```

**Containerisation:**
- `Dockerfile.backend` — Python 3.12-slim base, `uv` for dependency management, copies application modules individually for optimal Docker layer caching
- `Dockerfile.frontend` — Multi-stage build: Node 22 for Angular production build, nginx 1.27 for static serving
- `docker-compose.yml` — Local development orchestration with health checks
- `docker-compose.prod.yml` — Production with ECR image references and `awslogs` driver for CloudWatch

**Infrastructure (Terraform):**
- EC2 instance (`t3.small`, 2 vCPU, 2 GB RAM) with 2 GB swap file
- ECR repositories for backend and frontend images
- Security group (HTTP port 80, SSH port 22)
- IAM instance profile for ECR pull and CloudWatch Logs access
- CloudWatch Log Groups with 7-day retention
- CloudWatch Alarms (instance health auto-recovery, high CPU)
- CloudWatch Dashboard (CPU, network, error logs, LLM latency)

**Nginx reverse proxy** handles:
- SPA routing (`try_files $uri $uri/ /index.html`)
- API reverse proxy (`/api/*` → `http://backend:8000`)
- SSE support (`proxy_buffering off`)
- LLM timeout accommodation (`proxy_read_timeout 120s`)
- Resume upload size (`client_max_body_size 10m`)

### 3.3 Data Flow and Integration Points

1. **User → Angular SPA** — Chat messages, resume file upload (drag-drop/paste/file picker)
2. **Angular → FastAPI** — REST API calls via `HttpClient` with interceptor prepending `apiUrl`
3. **FastAPI → LangGraph** — Session state passed through compiled `StateGraph`; orchestrator routes to agents
4. **Agents → External APIs** — Adzuna (job search), Tavily (web search), Wikipedia (company research), OpenAI (LLM + embeddings)
5. **Agents → ChromaDB** — Vector similarity search for courses, trends, job matching
6. **FastAPI → Angular** — SSE streaming for real-time pipeline progress; JSON responses for results
7. **Docker → CloudWatch** — Container stdout/stderr streamed via `awslogs` driver

### 3.4 Justification of Architectural Styles and Technology Choices

| Technology | Justification |
|---|---|
| **LangGraph** | Provides stateful, graph-based orchestration with conditional edges — ideal for FSM-based multi-agent pipelines with HITL checkpoints |
| **LangChain** | Standardised LLM interface with prompt templates, output parsing, and tool integration |
| **ChromaDB** | Lightweight, in-process vector database — no external server needed, seeds from JSON files |
| **FastAPI** | Async Python web framework with automatic OpenAPI docs, Pydantic validation, and SSE support |
| **Angular 20** | Enterprise-grade SPA framework with signals, standalone components, and Material Design 3 |
| **OpenAI GPT-4o / GPT-4o-mini** | Model router selects quality model (GPT-4o) for complex tasks and cost-effective model (GPT-4o-mini) for routing/simple tasks |
| **Terraform** | Infrastructure-as-code for reproducible, version-controlled AWS provisioning with one-command teardown |
| **Docker + Docker Compose** | Consistent build/runtime environment, multi-service orchestration, health checks |
| **GitHub Actions** | Integrated CI/CD with native AWS ECR/EC2 support and SSH deployment |

---

## 4. Agent Roles and Design

### 4.1 Orchestrator Agent

**Purpose:** FSM-based pipeline controller that determines the next action based on user intent and current pipeline state.

**Reasoning Pattern:** The orchestrator uses an LLM (GPT-4o-mini) as an intent classifier. Given the user's message and current pipeline state, it classifies the intent into one of the named stages. A system prompt provides the valid actions and current context (which stages have been completed, what data is available).

**Planning and Memory:**
- **FSM state machine** with 11 named stages and explicit transition rules (e.g., `parsing` → `parsing_review` or `discovery`)
- **Decision log** — every routing decision is recorded with timestamp, stage, action, and reasoning for full traceability
- **Stage history** — tracks all stage transitions for audit

**Tools:** LLM-based intent classification via `ChatOpenAI`

**Communication Protocol:** The orchestrator reads from and writes to a shared `JobAIdState` TypedDict. It sets `current_stage` and `last_action` which the downstream agent nodes use to determine what to execute.

**Bounded Autonomy:**
- Maximum 20 iterations per session
- Maximum 2 retries per stage
- Maximum 50 LLM calls per session
- Automatic halt and error reporting on limit breach

**Fallback Strategy:** If the LLM fails to classify intent, the orchestrator falls back to a deterministic stage progression based on the current stage and available data.

### 4.2 Resume Parser Agent

**Purpose:** Extract structured information from raw resume text using LLM-powered NLP, assess parsing confidence, and produce a de-biased copy for downstream processing.

**Reasoning Pattern:** Single-shot LLM extraction with structured JSON output. The prompt instructs the LLM to extract contact info, professional summary, skills, experience, and education into a defined schema.

**Planning and Memory:**
- Stores `resume_info` (full parsed data), `resume_debiased` (PII-stripped), `parsing_confidence` (0.0-1.0), and `missing_fields` in shared state
- Results appended to the `results` array for persistence across conversation turns

**Tools:**
- `ChatOpenAI` (GPT-4o) for structured extraction
- `PII Sanitiser` — strips name, email, phone, and gender indicators to produce `resume_debiased`
- Input filter validates resume text before processing (length limits, injection detection)

**Fallback Strategy:** If LLM parsing fails, a regex-based fallback extracts basic fields (name, email, skills keywords).

### 4.3 Job Discovery and Matching Agent

**Purpose:** Search for relevant job listings, store them in a vector database for semantic matching, and rank them against the candidate's profile using LLM-powered scoring.

**Reasoning Pattern:** Multi-step pipeline — (1) API search → (2) vector upsert → (3) semantic retrieval → (4) LLM-powered scoring with rubric.

**Planning and Memory:**
- Stores `job_listings` (raw API results), `scored_jobs` (ranked with scores 0-100), and `matching_explanation` in shared state
- Uses de-biased resume for scoring to mitigate bias

**Tools:**
- `Adzuna API` — real job board search with location, keyword, and salary filters
- `ChromaDB` — upserts job listings as vectors, retrieves top matches via semantic similarity
- `ChatOpenAI` (GPT-4o) — scores and ranks jobs against candidate profile
- `MOCK_JOBS` fallback — 23 pre-defined job listings when Adzuna API is unavailable

**Communication:** Reads `resume_debiased` and `job_query` from state; writes `scored_jobs` with title, company, score, URL, and explanation.

### 4.4 Market Intelligence Agent

**Purpose:** Analyse skill gaps, generate an upskilling roadmap with specific course recommendations, provide salary benchmarks, and identify industry trends.

**Reasoning Pattern:** RAG-augmented analysis — retrieves relevant data from ChromaDB vector store and Tavily web search, then synthesises with LLM.

**Planning and Memory:**
- Stores `skill_gaps` (prioritised list), `upskilling_roadmap` (courses with providers, URLs, durations), `salary_insights` (range, median, percentiles), and `industry_trends` in shared state

**Tools:**
- `ChromaDB` — semantic search over seeded courses (15 entries) and industry trends (12 articles)
- `Tavily Web Search` — real-time search for courses, trends, and salary data
- `ChatOpenAI` (GPT-4o) — synthesises RAG context into structured recommendations
- Seed data fallback — JSON salary benchmarks (18 entries for Singapore market)

**Fallback Strategy:** If Tavily API is unavailable, falls back to ChromaDB seed data. If ChromaDB has no relevant results, provides LLM-only analysis.

### 4.5 Pitch Generator Agent

**Purpose:** Generate a tailored cover letter through multi-step prompt chaining with company-specific research.

**Reasoning Pattern:** 4-step prompt chain:
1. **Company Research** — Wikipedia REST API + Tavily web search for company background, products, culture
2. **Match Analysis** — LLM analyses overlap between candidate profile and job requirements
3. **Draft Generation** — LLM generates cover letter incorporating company research and match analysis
4. **Quality Review** — LLM self-reviews the draft for tone, specificity, and completeness

**Planning and Memory:**
- Stores `draft_pitches` (intermediate drafts with review feedback) and `final_pitch` in shared state
- Reads from `scored_jobs` (target job), `resume_info` (candidate profile), and `skill_gaps`

**Tools:**
- `Wikipedia REST API` — company summary retrieval with disambiguation handling
- `Tavily Web Search` — supplementary company research
- `ChatOpenAI` (GPT-4o) — all 4 prompt chain steps

### 4.6 Summarizer Agent

**Purpose:** Generate a comprehensive, grounded summary report covering all pipeline results with a decision log for full traceability.

**Reasoning Pattern:** Single-shot LLM generation with full session state as context. The prompt includes all agent outputs (resume info, scored jobs, skill gaps, salary data, cover letter) and instructs the LLM to produce a structured markdown report.

**Planning and Memory:**
- Reads entire session state (all results from all agents)
- Stores `summary` (markdown report) and validates with `check_grounding()` to ensure the summary references actual data from the state

**Tools:**
- `ChatOpenAI` (GPT-4o) — report generation
- `Output filter` — grounding check (0.0-1.0 score) verifying the summary references the candidate's name, top company, and skill gaps

**Coordination:** Runs as the final agent after all others have completed, ensuring full state availability.

### 4.7 Inter-Agent Communication

All agents communicate via the **shared `JobAIdState` TypedDict** — a flat state object managed by LangGraph. Each agent reads its required inputs from state and writes its outputs back. The orchestrator coordinates execution order via FSM transitions. There is no direct agent-to-agent messaging; all coordination flows through the state graph.

---

## 5. Explainable and Responsible AI Practices

### 5.1 Alignment with Explainable AI Principles

| Development Stage | Explainability Measure |
|---|---|
| **Resume Parsing** | Confidence score (0.0-1.0) reported to user; missing fields explicitly listed; parsing rationale logged |
| **Job Matching** | Each scored job includes a `matching_explanation` describing why it was ranked; scores are transparent (0-100 rubric) |
| **Market Intelligence** | Skill gaps are prioritised with reasoning; upskilling courses include provider, duration, and relevance |
| **Pitch Generation** | Multi-step chain is logged — company research, match analysis, draft, review — showing how the cover letter was constructed |
| **Summarization** | Decision log captures every orchestrator decision with timestamp and reasoning; grounding score validates factual accuracy |

### 5.2 Fairness and Bias Mitigation

**PII De-biasing Pipeline:**

The `pii_sanitizer.py` module implements a de-biasing strategy for resume processing:

1. **Name removal** — `contact_info.name` is stripped before downstream processing to prevent name-based bias
2. **Email removal** — email addresses removed to prevent domain-based bias (e.g., university prestige)
3. **Phone removal** — phone numbers stripped to prevent location-based bias
4. **Gender indicator removal** — pronouns (`he`, `she`, `him`, `her`) and titles (`Mr`, `Ms`, `Mrs`, `Miss`) are removed from the professional summary

The de-biased resume (`resume_debiased`) is used for job scoring and matching, while the full resume is preserved for the user-facing summary.

### 5.3 Transparency and Traceability

- **Decision log** — every orchestrator routing decision is timestamped and recorded with the action taken and reasoning
- **Stage history** — full audit trail of pipeline stage transitions
- **Results array** — append-only storage of all agent outputs; running an agent twice preserves both results
- **Grounding check** — the summariser's output is validated against actual session data to detect hallucination

### 5.4 Governance Framework Alignment

The system aligns with **IMDA's Model AI Governance Framework** principles:

| Principle | Implementation |
|---|---|
| **Transparency** | Decision log, stage history, matching explanations, confidence scores |
| **Fairness** | PII de-biasing, gender indicator removal, skill-based (not identity-based) matching |
| **Human Agency** | HITL review checkpoints at parsing, discovery, and pitching stages; user can approve/reject/provide feedback |
| **Accountability** | Bounded autonomy limits (max iterations, retries, LLM calls); structured logging with request IDs |
| **Robustness** | Input validation, output structure validation, graceful fallbacks for all external APIs |

---

## 6. AI Security Risk Register

| # | Risk | Category | Likelihood | Impact | Mitigation | Implementation |
|---|---|---|---|---|---|---|
| 1 | **Prompt Injection** | Input Attack | High | High | 7-pattern regex detection in `input_filter.py`; reject inputs matching injection patterns | `_INJECTION_PATTERNS` checks for "ignore previous instructions", "you are now", "system:", `<system>` tags, "ADMIN MODE", "jailbreak", "DAN mode" |
| 2 | **Resume Injection** | Input Attack | Medium | High | Input length limit (50KB); spotlight delimiter wrapping (`<<<USER_INPUT>>>`) | `validate_resume_text()` enforces `MAX_INPUT_LENGTH = 50,000`; `spotlight_wrap()` isolates user content |
| 3 | **Query Injection** | Input Attack | Medium | Medium | Query length limit (500 chars); same injection pattern detection | `validate_job_query()` enforces `MAX_QUERY_LENGTH = 500` |
| 4 | **Hallucination** | LLM Output | High | Medium | Output structure validation; grounding check against session state | `validate_resume_output()`, `validate_job_discovery_output()`, `validate_pitch_output()`, `check_grounding()` in `output_filter.py` |
| 5 | **Runaway Agent Loops** | Agent Autonomy | Medium | High | Bounded autonomy with hard limits | `BoundedAutonomy` class: max 20 iterations, max 2 retries/stage, max 50 LLM calls per session |
| 6 | **PII Leakage** | Data Privacy | Medium | High | PII stripping before downstream processing | `strip_pii()` removes name, email, phone; `sanitize_text()` redacts emails/phones from raw text |
| 7 | **Gender Bias** | Fairness | Medium | Medium | Gender indicator removal from professional summary | `_GENDER_INDICATORS` set strips pronouns and titles before job matching |
| 8 | **API Key Exposure** | Secret Management | Low | Critical | Environment variables, `.env` not baked into Docker images | `env_file: .env` in docker-compose; GitHub Secrets for CI/CD; `.env` in `.gitignore` |
| 9 | **Dependency Vulnerabilities** | Supply Chain | Medium | Medium | Automated dependency scanning in CI | `pip-audit` for Python, `npm audit` for frontend in GitHub Actions CI pipeline |
| 10 | **Adversarial Job Listings** | External Data | Low | Medium | Output validation on job structure; LLM-powered relevance filtering | `validate_job_discovery_output()` checks required fields; scoring rubric filters irrelevant results |

---

## 7. MLSecOps / LLMSecOps Pipeline

### 7.1 CI/CD Pipeline Diagram

```
┌──────────┐     ┌─────────────────────────────┐     ┌──────────────────────────┐     ┌─────────────┐
│  Push to  │────►│   CI: Tests & Quality       │────►│  Build & Push to ECR     │────►│ Deploy to   │
│  main     │     │                             │     │                          │     │ EC2         │
│           │     │  ┌───────────────────────┐  │     │  ┌────────────────────┐  │     │             │
│           │     │  │ Backend Tests         │  │     │  │ docker build       │  │     │ SSH into    │
│           │     │  │ - pytest (92 tests)   │  │     │  │ - backend image    │  │     │ EC2         │
│           │     │  │ - AI security tests   │  │     │  │ - frontend image   │  │     │             │
│           │     │  └───────────────────────┘  │     │  └────────────────────┘  │     │ docker pull │
│           │     │  ┌───────────────────────┐  │     │  ┌────────────────────┐  │     │             │
│           │     │  │ Security Scan         │  │     │  │ Tag: git SHA +     │  │     │ docker      │
│           │     │  │ - pip-audit           │  │     │  │       latest       │  │     │ compose up  │
│           │     │  │ - npm audit           │  │     │  └────────────────────┘  │     │             │
│           │     │  └───────────────────────┘  │     │  ┌────────────────────┐  │     │ Health      │
│           │     │                             │     │  │ Push to ECR        │  │     │ check       │
└──────────┘     └─────────────────────────────┘     │  └────────────────────┘  │     └─────────────┘
                                                     └──────────────────────────┘
```

### 7.2 Automated Testing (Including AI Security Tests)

The CI pipeline runs **92 automated tests** on every push/PR:

| Test Category | File | Tests | Description |
|---|---|---|---|
| **AI Security** | `test_input_filter.py` | 19 | Prompt injection detection (all 7 patterns), adversarial bypass attempts, length enforcement |
| **Output Validation** | `test_output_filter.py` | 14 | Structure validation for resume/job/pitch outputs, grounding score calculation |
| **Bounded Autonomy** | `test_bounded_autonomy.py` | 14 | Iteration/retry/LLM-call limit enforcement and reset behaviour |
| **PII Sanitisation** | `test_pii_sanitizer.py` | 14 | PII stripping, gender indicator removal, text redaction |
| **Health Endpoint** | `test_health.py` | 5 | API health check response validation |
| **Session Lifecycle** | `test_sessions.py` | 7 | CRUD operations, 404 handling |

Security scans include:
- **`pip-audit`** — checks Python dependencies for known vulnerabilities (CVE database)
- **`npm audit`** — checks frontend dependencies for known vulnerabilities

### 7.3 Versioning and Tracking

- **Docker image tags** — each build is tagged with the git commit SHA and `latest`, enabling rollback to any specific version
- **Application version** — `version: "0.2.0"` in `pyproject.toml` and reported by `/api/health` endpoint
- **Terraform state** — remote S3 backend with DynamoDB locking for infrastructure version control
- **Git** — all code, configuration, and infrastructure changes tracked in version control

### 7.4 Deployment Strategy

**Local Development:**
```bash
docker compose build && docker compose up -d
```

**Production Deployment (automated via GitHub Actions):**
1. Push to `main` triggers CI tests
2. On success, Docker images are built and pushed to ECR
3. GitHub Actions SSHs into EC2, pulls latest images, and runs `docker compose up -d`
4. Health check verifies the deployment succeeded

**Infrastructure Provisioning (Terraform):**
```bash
cd infra && bash bootstrap.sh   # One-time: S3 state backend
terraform init && terraform apply  # Provision ECR + EC2 + CloudWatch
terraform destroy                  # Teardown all resources
```

### 7.5 Monitoring and Alerting

**Structured JSON Logging:**
- Every API request is logged with `timestamp`, `request_id`, `method`, `path`, `status`, `duration`
- LLM calls are tracked with `model`, `task_type`, `prompt_tokens`, `completion_tokens`, `latency_ms`
- Per-session aggregate summaries (total calls, tokens, latency)

**CloudWatch Integration:**
- Container stdout/stderr streams directly to CloudWatch via `awslogs` Docker driver
- Log Groups: `/jobaid/backend`, `/jobaid/frontend` with 7-day retention
- Alarms: instance health (auto-recovery), high CPU (>80% for 5 minutes)
- Dashboard: CPU utilisation, network I/O, error logs, LLM latency

**Health Check Endpoint:**

`GET /api/health` returns system status including ChromaDB connectivity and environment variable checks:
```json
{
  "status": "healthy",
  "version": "0.2.0",
  "uptime_seconds": 3600,
  "checks": {
    "env_vars": "ok",
    "chromadb": "ok"
  }
}
```

### 7.6 Logging and Auditability

| Log Type | Source | Format | Destination |
|---|---|---|---|
| API request logs | `api/middleware.py` | Structured JSON | stdout → CloudWatch |
| LLM call logs | `utils/llm_logger.py` | Structured JSON | stdout → CloudWatch |
| Decision logs | `agents/orchestrator.py` | JSON in session state | API response |
| Stage history | `models/state.py` | Array in session state | API response |
| Agent errors | `graph/nodes.py` | JSON error entries | stdout + session state |

---

## 8. Testing Summary

### 8.1 Types of Tests Performed

| Type | Tests | Scope |
|---|---|---|
| **Unit Tests** | 42 | Individual guardrail functions (input filter, output filter, bounded autonomy, PII sanitiser) |
| **Integration Tests** | 12 | FastAPI endpoint testing (health check, session CRUD lifecycle) via TestClient |
| **AI Security Tests** | 19 | Prompt injection detection (all 7 patterns), adversarial inputs (case variations, extra whitespace, Unicode), input length enforcement |
| **Dependency Security Scans** | 2 jobs | `pip-audit` (Python CVEs), `npm audit` (frontend CVEs) |

### 8.2 Test Results

```
======================== 92 passed, 2 warnings in 2.91s ========================

tests/test_bounded_autonomy.py   14 passed
tests/test_health.py              5 passed
tests/test_input_filter.py       19 passed
tests/test_output_filter.py      14 passed
tests/test_pii_sanitizer.py      14 passed
tests/test_sessions.py            7 passed
```

All 92 tests pass. The 2 warnings are deprecation notices for FastAPI's `on_event` (informational only, non-blocking).

### 8.3 Key AI Security Test Findings

The prompt injection tests validate that all 7 detection patterns correctly reject adversarial inputs while allowing legitimate technical resumes that contain words like "system" (e.g., "distributed systems design") or "admin" (e.g., "database administrator"). Adversarial bypass attempts including case variations (`IGNORE ALL PREVIOUS INSTRUCTIONS`), extra whitespace (`ignore   all   previous   instructions`), and mixed case (`Ignore Previous Instructions`) are all caught.

---

## 9. Reflection

### 9.1 What Went Well

- **Agentic architecture** — the FSM-based orchestrator with LangGraph provided clean separation of agent responsibilities and predictable pipeline behaviour
- **RAG integration** — combining ChromaDB vector search with Tavily web search and seed data fallbacks created a robust information retrieval layer
- **Guardrails** — layered defence (input validation, output validation, bounded autonomy, PII de-biasing) provided defence-in-depth without over-engineering
- **Containerisation and IaC** — Docker + Terraform enabled reproducible deployments and one-command teardown, keeping cloud costs under control

### 9.2 Challenges Encountered

- **LLM output parsing** — LLMs occasionally return malformed JSON despite explicit schema instructions; required robust fallback parsing and retry logic
- **API rate limits** — Adzuna free tier (250 req/day) and Tavily free tier (1000 req/month) required careful fallback design
- **SSE streaming** — implementing real-time pipeline progress through nginx reverse proxy required careful proxy configuration (`proxy_buffering off`)
- **Testing with heavy dependencies** — unit tests for API endpoints required mocking the LangGraph/LangChain dependency chain to avoid importing the full agent stack

### 9.3 Future Improvements

- **Persistent storage** — replace in-memory session store with Redis or PostgreSQL for session persistence across restarts
- **Streaming LLM responses** — stream agent outputs token-by-token to the UI for better perceived latency
- **Multi-language support** — extend resume parsing to handle non-English resumes
- **Fine-tuned models** — train a smaller, specialised model for intent classification to reduce latency and cost compared to GPT-4o-mini
- **Load testing** — implement k6 or Locust load tests to validate concurrent session handling
- **Observability** — add OpenTelemetry distributed tracing for end-to-end request visibility across agents

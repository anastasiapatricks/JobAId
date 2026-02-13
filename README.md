# JobAId — LLM-Powered Multi-Agent Job Search Assistant

An AI-powered job search assistant built with **LangGraph**, **LangChain**, **ChromaDB**, **FastAPI**, and an **Angular 20** chat-based frontend. JobAId parses resumes using LLM-based NLP, discovers and ranks jobs via semantic matching, provides market intelligence with RAG-powered upskilling recommendations, and generates tailored cover letters through multi-step prompt chaining.

## Overview

JobAId runs a pipeline of 5 specialised agents coordinated by an FSM-based orchestrator:

| Agent | Responsibility |
|---|---|
| **Orchestrator** | FSM-based pipeline controller with named stages, conditional transitions, HITL review checkpoints, and bounded autonomy |
| **Resume Parser** | LLM-powered structured extraction (skills, experience, education), confidence assessment, PII de-biasing |
| **Job Discovery & Matching** | Adzuna API search (MOCK_JOBS fallback), ChromaDB semantic matching, LLM-powered ranking with scoring rubric |
| **Market Intelligence** | Skill gap analysis, RAG-powered upskilling roadmap with course recommendations, salary benchmarks, industry trends |
| **Pitch Generator** | 4-step prompt chaining: company research (Wikipedia) → match analysis → draft generation → quality review |
| **Summarizer** | Grounded explainability — summarises only structured state data, includes decision log for transparency |

## Architecture

```
                        +-----------+
                        |   START   |
                        +-----+-----+
                              |
                              v
                      +-------+--------+
               +------| ORCHESTRATOR   |------+
               |      +-------+--------+      |
               |          |       |            |
               v          v       v            v
        +-----------+ +--------+ +----------+ +----------+
        |  RESUME   | |  JOB   | |  MARKET  | |  PITCH   |
        |  PARSER   | | DISCOV | |  INTEL   | |  GEN     |
        +-----------+ +--------+ +----------+ +----------+
               |          |       |            |
               +----------+-------+------------+
                              |
                              v
                      +-------+--------+
                      |  SUMMARIZER    |
                      +-------+--------+
                              |
                              v
                        +-----+-----+
                        |    END    |
                        +-----------+
```

**Pipeline flow:** `intake → parsing → [review] → discovery → [review] → market_intel → pitching → [review] → summarizing → complete`

Review stages are optional HITL (Human-in-the-Loop) checkpoints.

## Key Features

- **LLM-powered NLP** — all agents use OpenAI models for extraction, analysis, and generation (regex fallback when LLM fails)
- **RAG with ChromaDB** — vector search over courses, industry trends, and job listings using `text-embedding-3-small`
- **Real job API** — Adzuna integration with automatic MOCK_JOBS fallback when API keys are not configured
- **FSM orchestrator** — named stages with valid transitions (not index-based), error recovery, max 2 retries per stage
- **Guardrails** — prompt injection detection, PII sanitisation, input/output validation, bounded autonomy (max 20 iterations, max 50 LLM calls)
- **De-biasing** — PII (name, email, phone, gender indicators) stripped before downstream processing
- **Grounded summarisation** — summariser uses only structured state data, temperature=0, with decision log
- **Three-tier architecture** — Angular 20 chat UI, FastAPI REST API, and CLI

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd PracticeModule-Team31
```

### 2. Install Dependencies

This project uses [uv](https://docs.astral.sh/uv/) for dependency management (Python 3.12+).

```bash
uv sync
```

### 3. Configure Environment Variables

Create a `.env` file in the project root:

```env
# Required
OPENAI_API_KEY=your_openai_api_key_here

# Optional — Adzuna job board API (falls back to mock data if not set)
ADZUNA_APP_ID=your_adzuna_app_id
ADZUNA_API_KEY=your_adzuna_api_key

# Optional
DEBUG=true
```

Get your OpenAI API key from: https://platform.openai.com/api-keys

Get Adzuna API credentials (free tier, 250 req/day) from: https://developer.adzuna.com/

### 4. Run the CLI

```bash
uv run python -m cli.main
```

You will be prompted to:
1. Enter the path to a resume file (e.g. `sample_resume.txt`)
2. Enter job search keywords (e.g. `python backend engineer`)
3. Optionally enter a preferred location

The pipeline will run all agents and display results including job matches, skill gaps, upskilling roadmap, salary insights, and a generated cover letter.

### 5. Run the API Server (Backend)

```bash
uv run uvicorn api.app:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### 6. Run the Frontend

Requires **Node.js 24+** and **npm 11+**.

```bash
cd frontend
npm install
npm start
```

The Angular dev server will start at `http://localhost:4200`. It connects to the backend at `http://localhost:8000` — make sure the API server (step 5) is running first.

#### Frontend Chat Flow

1. The app opens with a welcome message and prompts you to upload a resume
2. Drag-and-drop a file (PDF/TXT), use the file picker, or paste resume text directly
3. Enter a job query (e.g. "python backend engineer in Singapore")
4. The pipeline runs — a progress stepper shows real-time stage updates as the backend polls
5. Results appear inline in the chat: executive summary, ranked job matches with score badges, skill gap chips, upskilling roadmap, salary range bar, cover letter with copy button, and an expandable decision log

#### API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/sessions` | Create a new session |
| `GET` | `/api/sessions` | List all sessions |
| `GET` | `/api/sessions/{id}` | Get session info |
| `DELETE` | `/api/sessions/{id}` | Delete a session |
| `POST` | `/api/sessions/{id}/resume` | Upload a resume file |
| `POST` | `/api/sessions/{id}/run` | Start the pipeline (async) |
| `GET` | `/api/sessions/{id}/status` | Poll pipeline progress |
| `POST` | `/api/sessions/{id}/approve` | HITL approval |
| `GET` | `/api/sessions/{id}/results` | Get final results |

#### Example API Usage

```bash
# Create session
curl -X POST http://localhost:8000/api/sessions -H "Content-Type: application/json" -d '{}'

# Upload resume
curl -X POST http://localhost:8000/api/sessions/{session_id}/resume -F "file=@sample_resume.txt"

# Run pipeline
curl -X POST http://localhost:8000/api/sessions/{session_id}/run \
  -H "Content-Type: application/json" \
  -d '{"resume_text": "Name: John Tan\nSkills: Python, Docker, AWS\nExperience: 5 years", "job_query": "python backend engineer"}'

# Poll status
curl http://localhost:8000/api/sessions/{session_id}/status

# Get results
curl http://localhost:8000/api/sessions/{session_id}/results
```

## Project Structure

```
PracticeModule-Team31/
├── config/
│   ├── settings.py              # Pydantic BaseSettings, env vars
│   └── prompts.py               # All system prompts (single source of truth)
├── models/
│   ├── state.py                 # JobAIdState TypedDict (FSM, HITL, all agent outputs)
│   ├── schemas.py               # Pydantic models: ResumeInfo, JobListing, SkillGap, etc.
│   └── api_models.py            # FastAPI request/response models
├── agents/
│   ├── orchestrator.py          # FSM orchestrator with bounded autonomy
│   ├── resume_parser.py         # LLM extraction + confidence + PII de-biasing
│   ├── job_discovery.py         # Adzuna API + ChromaDB + LLM ranking
│   ├── market_intelligence.py   # Skill gaps, upskilling, salary, trends (RAG)
│   ├── pitch_generator.py       # 4-step prompt chaining cover letter
│   └── summarizer.py            # Grounded explainability summariser
├── tools/
│   ├── job_board_api.py         # Adzuna API integration + MOCK_JOBS fallback
│   ├── job_scrape.py            # MOCK_JOBS data (23 listings)
│   ├── wikipedia.py             # Wikipedia REST API with disambiguation fallback
│   ├── chromadb_tools.py        # ChromaDB search/upsert helpers
│   └── pii_sanitizer.py         # PII detection + de-biasing
├── vectordb/
│   ├── collections.py           # ChromaDB collections (jobs, courses, trends)
│   ├── embeddings.py            # OpenAI text-embedding-3-small
│   └── seed_data.py             # Seed collections from JSON
├── guardrails/
│   ├── input_filter.py          # Prompt injection defense, input validation
│   ├── output_filter.py         # Output validation, grounding check
│   ├── model_router.py          # LLM model selection by task type
│   └── bounded_autonomy.py      # Iteration/retry/LLM-call limits
├── graph/
│   ├── builder.py               # LangGraph StateGraph construction
│   └── nodes.py                 # Node wrappers with error boundaries
├── api/
│   ├── app.py                   # FastAPI application factory
│   ├── dependencies.py          # Session store, graph singleton
│   ├── middleware.py             # CORS, request logging
│   └── routes/
│       ├── sessions.py          # Session CRUD
│       ├── pipeline.py          # Run, status, approve, results
│       ├── resume.py            # Resume file upload
│       └── health.py            # Health check
├── frontend/                    # Angular 20 chat-based UI
│   ├── src/app/
│   │   ├── app.ts               # Shell: toolbar + router-outlet
│   │   ├── app.config.ts        # Providers: router, httpClient, animations
│   │   ├── app.routes.ts        # Routes: / and /session/:id
│   │   ├── core/
│   │   │   ├── models/          # TypeScript interfaces (session, pipeline, results, resume)
│   │   │   ├── services/        # ApiService, SessionService, PipelineService, ChatService
│   │   │   └── interceptors/    # API URL interceptor (prepends backend base URL)
│   │   ├── features/
│   │   │   ├── chat/            # Chat page, message list, message bubble, input, typing indicator
│   │   │   ├── resume/          # Resume upload (drag-drop + paste) and preview
│   │   │   ├── pipeline/        # Pipeline progress stepper (5 stages)
│   │   │   └── results/         # Job cards, skill gaps, upskilling roadmap, salary bar,
│   │   │                        #   cover letter, summary, decision log
│   │   ├── shared/              # Toolbar, file drop zone, copy button, auto-scroll directive,
│   │   │                        #   score-color pipe
│   │   └── environments/        # Dev (localhost:8000) and prod API URLs
│   ├── angular.json
│   └── package.json
├── cli/
│   └── main.py                  # CLI entry point
├── data/
│   ├── seed_courses.json        # 15 course catalog entries
│   ├── seed_salary_data.json    # 18 salary benchmarks (Singapore)
│   └── seed_industry_trends.json # 12 industry trend articles
├── tests/
├── sample_resume.txt
├── sample_resume_oth.txt
├── pyproject.toml
├── utils.py
└── README.md
```

## Seed Data

ChromaDB is automatically seeded on startup with:

| Collection | Entries | Source |
|---|---|---|
| `courses_and_resources` | 15 courses | `data/seed_courses.json` |
| `industry_trends` | 12 trend articles | `data/seed_industry_trends.json` |
| `jobs` | Dynamic per run | Adzuna API / MOCK_JOBS |

Salary benchmarks (18 entries) are loaded as structured JSON from `data/seed_salary_data.json`.

## Dependencies

### Backend (Python 3.12+)

- **LangGraph / LangChain** — multi-agent orchestration
- **langchain-openai** — OpenAI LLM and embedding integration
- **ChromaDB** — vector database for RAG
- **FastAPI / Uvicorn** — REST API backend
- **Pydantic / pydantic-settings** — data validation and configuration
- **httpx** — HTTP client (Adzuna API)
- **beautifulsoup4** — HTML parsing
- **python-dotenv** — environment variable management

### Frontend (Node.js 24+)

- **Angular 20** — standalone components, signals, control flow syntax
- **Angular Material 20** — Material 3 design components (toolbar, cards, chips, stepper, expansion panels)
- **RxJS** — polling pipeline status with `interval` + `switchMap`
- **TypeScript 5.9** — strict mode

## Credits

Developed for NUS-ISS Practice Module
Authors: Sanath, Anastasia, Hany, Vincent (Team 31)

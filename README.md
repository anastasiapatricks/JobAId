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
| **Summarizer** | Grounded explainability — feeds full session state (all results) to the LLM, generates markdown report with decision log |

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
- **Results persistence** — all agent outputs stored in an append-only results array; e.g. running the same agent twice preserves both results
- **Grounded summarisation** — summariser receives full session state (all results), generates markdown report with decision log
- **Web search augmentation** — Tavily API for real-time course lookups, trend research, salary data, and company research (with RAG/seed-data fallbacks)
- **Three-tier architecture** — Angular 20 chat UI, FastAPI REST API, and CLI

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd <project-root>
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

# Optional — Tavily web search for courses, trends, salary, company research
TAVILY_API_KEY=your_tavily_api_key

# Optional
DEBUG=true
```

Get your OpenAI API key from: https://platform.openai.com/api-keys

Get Adzuna API credentials (free tier, 250 req/day) from: https://developer.adzuna.com/

Get Tavily API key (free tier, 1000 req/month) from: https://tavily.com/

### 4. Run the API Server (Backend)

```bash
uv run uvicorn api.app:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### 5. Run the Frontend

Requires **Node.js 24+** and **npm 11+**.

```bash
cd frontend
npm install
npm start
```

The Angular dev server will start at `http://localhost:4200`. It connects to the backend at `http://localhost:8000` — make sure the API server (step 4) is running first.

#### Frontend Chat Flow

1. The app opens with a welcome message and prompts you to upload a resume
2. Drag-and-drop a file (PDF/DOCX/TXT), use the file picker, or paste resume text directly
3. Your resume is parsed and the assistant greets you with a summary of your skills
4. Chat naturally — ask to search for jobs, analyze the market, write cover letters, or get a summary
5. Each agent result appears inline in the chat. You can run the same agent multiple times (e.g. search for different roles, generate multiple cover letters) — all results are preserved
6. Ask for a summary to get a markdown-formatted report covering everything in the session

#### API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/sessions` | Create a new session |
| `GET` | `/api/sessions` | List all sessions |
| `GET` | `/api/sessions/{id}` | Get session info |
| `DELETE` | `/api/sessions/{id}` | Delete a session |
| `POST` | `/api/sessions/{id}/resume` | Upload a resume file |
| `POST` | `/api/sessions/{id}/run` | Parse resume and start session (async) |
| `POST` | `/api/sessions/{id}/step` | Send a chat message — orchestrator routes to the right agent |
| `GET` | `/api/sessions/{id}/status` | Poll agent execution progress |
| `POST` | `/api/sessions/{id}/approve` | HITL approval |
| `GET` | `/api/sessions/{id}/results` | Get all results (append-only array of agent outputs) |

#### Example API Usage

```bash
# Create session
curl -X POST http://localhost:8000/api/sessions -H "Content-Type: application/json" -d '{}'

# Upload resume
curl -X POST http://localhost:8000/api/sessions/{session_id}/resume -F "file=@sample_resume.txt"

# Parse resume (starts async — poll /status until awaiting_input)
curl -X POST http://localhost:8000/api/sessions/{session_id}/run \
  -H "Content-Type: application/json" \
  -d '{"resume_text": "Name: John Tan\nSkills: Python, Docker, AWS\nExperience: 5 years", "job_query": ""}'

# Chat — search for jobs (orchestrator routes to the discovery agent)
curl -X POST http://localhost:8000/api/sessions/{session_id}/step \
  -H "Content-Type: application/json" \
  -d '{"message": "Find python backend engineer jobs in Singapore"}'

# Poll status until awaiting_input
curl http://localhost:8000/api/sessions/{session_id}/status

# Chat — generate a cover letter
curl -X POST http://localhost:8000/api/sessions/{session_id}/step \
  -H "Content-Type: application/json" \
  -d '{"message": "Write a cover letter for the first job"}'

# Get all results (array of every agent run)
curl http://localhost:8000/api/sessions/{session_id}/results
```

The `/results` endpoint returns an append-only `results` array — each agent run is a separate entry with `action`, `timestamp`, and its output fields. Running the same agent multiple times appends new entries without overwriting previous ones.

### Optional: Run the CLI

The CLI is a standalone alternative to the web UI. It is **not required** to run the backend + frontend.

```bash
uv run python -m cli.main
```

You will be prompted to enter a resume file path, job search keywords, and optionally a preferred location. The pipeline will run all agents sequentially and display results in the terminal.

## Project Structure

```
<project-root>/
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
│   ├── tavily_search.py         # Tavily web search (courses, trends, salary, company)
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
│   ├── conftest.py                # Shared test fixtures
│   ├── test_input_filter.py       # AI security tests (prompt injection)
│   ├── test_output_filter.py      # Output validation tests
│   ├── test_bounded_autonomy.py   # Autonomy limit tests
│   ├── test_pii_sanitizer.py      # PII sanitization tests
│   ├── test_health.py             # Health endpoint tests
│   └── test_sessions.py           # Session lifecycle tests
├── infra/
│   ├── main.tf                    # ECR + EC2 + SG + IAM + CloudWatch
│   ├── cloudfront.tf              # CloudFront CDN distribution (HTTPS)
│   ├── dashboard.tf               # CloudWatch dashboard (22 widgets)
│   ├── variables.tf               # Terraform input variables
│   ├── outputs.tf                 # App URL, SSH, ECR URIs
│   ├── user_data.sh.tpl           # EC2 bootstrap script
│   ├── bootstrap.sh               # One-time S3 state backend setup
│   └── terraform.tfvars.example   # Variable template
├── nginx/
│   └── nginx.conf                 # SPA serving + API reverse proxy
├── .github/workflows/
│   ├── ci.yml                     # Tests + security scan
│   └── deploy.yml                 # Build → ECR → Deploy EC2
├── Dockerfile.backend             # Python 3.12-slim + uv
├── Dockerfile.frontend            # Multi-stage Node + nginx
├── docker-compose.yml             # Local dev orchestration
├── docker-compose.prod.yml        # Production with ECR + awslogs
├── .dockerignore
├── .env.example
├── sample_resume.txt
├── sample_resume_oth.txt
├── pyproject.toml
└── README.md
```

## Deployment

### Docker (Local)

Build and run both services locally with Docker Compose:

```bash
# 1. Copy and fill in environment variables
cp .env.example .env
# Edit .env with your API keys

# 2. Build and start
docker compose build
docker compose up -d

# 3. Verify
curl http://localhost/api/health
# Open http://localhost in your browser
```

The frontend (nginx) serves the Angular SPA on port 80 and reverse-proxies `/api/*` requests to the backend on port 8000. SSE streaming and 120s timeouts for LLM calls are pre-configured.

### Docker (Production — AWS EC2)

Production deployment uses **Terraform** to provision AWS infrastructure and **GitHub Actions** for CI/CD.

#### Prerequisites

- AWS account with an IAM user that has EC2, ECR, CloudWatch, and S3 permissions
- An existing EC2 key pair in `ap-southeast-1` for SSH access
- AWS CLI configured locally (`aws configure`)

#### 1. Bootstrap Terraform State Backend (one-time)

```bash
cd infra
bash bootstrap.sh
```

This creates an S3 bucket and DynamoDB table for Terraform remote state.

#### 2. Provision Infrastructure

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your key pair name, API keys, and SSH CIDR

terraform init
terraform apply
```

Terraform creates:
- 2 ECR repositories (`jobaid-backend`, `jobaid-frontend`)
- EC2 instance (`t3.nano`, ~$0.005/hr) with Docker pre-installed
- CloudFront distribution (HTTPS with AWS-managed SSL certificate, static asset caching)
- Security group (HTTP port 80, HTTPS port 443, SSH port 22)
- IAM instance profile (ECR pull + CloudWatch Logs)
- CloudWatch Log Groups (`/jobaid/backend`, `/jobaid/frontend`) with 7-day retention
- CloudWatch Alarms (instance health auto-recovery, high CPU)
- CloudWatch Dashboard (22 widgets — infrastructure, API health, LLM metrics, pipeline, sessions, guardrails)

After `terraform apply`, note the outputs:
```
app_url        = "https://d1234abcdef.cloudfront.net"
cloudfront_url = "https://d1234abcdef.cloudfront.net"
ssh_command    = "ssh -i your-key.pem ec2-user@ec2-x-x-x-x.ap-southeast-1.compute.amazonaws.com"
ecr_backend_url  = "123456789.dkr.ecr.ap-southeast-1.amazonaws.com/jobaid-backend"
ecr_frontend_url = "123456789.dkr.ecr.ap-southeast-1.amazonaws.com/jobaid-frontend"
dashboard_url  = "https://ap-southeast-1.console.aws.amazon.com/cloudwatch/..."
```

#### 3. Configure GitHub Secrets

Add these secrets to the GitHub repository (Settings → Secrets and variables → Actions):

| Secret | Purpose |
|--------|---------|
| `AWS_ACCESS_KEY_ID` | AWS credentials for ECR + deploy |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials |
| `OPENAI_API_KEY` | Passed to EC2 .env |
| `TAVILY_API_KEY` | Passed to EC2 .env |
| `ADZUNA_APP_ID` | Passed to EC2 .env |
| `ADZUNA_API_KEY` | Passed to EC2 .env |
| `EC2_SSH_KEY` | Private key (PEM) for SSH into EC2 |
| `EC2_HOST` | EC2 public DNS from terraform output |

#### 4. Deploy

Trigger a deploy manually from the **Actions tab** → **Deploy** workflow → **Run workflow**:

```
Manual trigger → Build & Push to ECR → Deploy to EC2
```

CI (tests + security scan) runs automatically on every push and PR to `main`.

#### 5. Teardown

Remove all AWS resources and stop all costs:

```bash
cd infra
terraform destroy
```

### Cost Summary

| Resource | Cost |
|----------|------|
| EC2 `t3.nano` | ~$0.005/hr (~$4/month) |
| CloudFront | Free tier (1 TB/month transfer) |
| ECR | Free tier (500 MB/month) |
| CloudWatch Logs | Minimal (7-day retention) |
| Elastic IP | Not used (free auto-assigned DNS) |
| **Teardown** | `terraform destroy` removes everything |

## Testing

### Run Tests

```bash
# Install dev dependencies
uv sync --all-extras

# Run all tests
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_input_filter.py -v
```

### Test Suite (92 tests)

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_input_filter.py` | 19 | Prompt injection detection (all 7 patterns), input length limits, spotlight wrapping, adversarial inputs |
| `test_output_filter.py` | 14 | Resume/job/pitch output validation, grounding score calculation |
| `test_bounded_autonomy.py` | 14 | Iteration limits, per-stage retry limits, LLM call limits, reset |
| `test_pii_sanitizer.py` | 14 | PII stripping (name, email, phone), gender indicator removal, text sanitization |
| `test_health.py` | 5 | Health endpoint: status, version, uptime, system checks |
| `test_sessions.py` | 7 | Session CRUD lifecycle, 404 handling |

### AI Security Tests

The `test_input_filter.py` file specifically tests prompt injection defense against all 7 detection patterns:
- `ignore previous/above/prior instructions`
- `you are now`
- `system:` prefix
- `<system>` tags
- `ADMIN MODE`
- `jailbreak`
- `DAN mode`

Also tests adversarial bypass attempts (case variations, extra whitespace, mixed case) and verifies that legitimate technical resumes containing words like "system" or "admin" pass validation.

## CI/CD Pipeline

### CI — Tests & Quality (`.github/workflows/ci.yml`)

Triggered on every push and PR to `main`:

1. **Backend Tests** — installs deps with `uv sync`, runs `pytest tests/ -v`
2. **Security Scan** — `pip-audit` for Python dependencies, `npm audit` for frontend dependencies

### Deploy — Build, Push, Deploy (`.github/workflows/deploy.yml`)

Triggered via **manual dispatch only** (`workflow_dispatch` from the Actions tab):

1. **Build & Push** — builds both Docker images, tags with git SHA + `latest`, pushes to ECR
2. **Deploy** — SSHs into EC2, pulls latest images, runs `docker compose up -d`, verifies health check

## Monitoring & Observability

### Structured Logging

All API requests are logged as structured JSON with:
- `timestamp`, `request_id`, `method`, `path`, `status`, `duration`

LLM calls are instrumented via `logged_invoke()` across all 6 agents and tracked in `utils/llm_logger.py` with:
- `model`, `task_type`, `prompt_tokens`, `completion_tokens`, `latency_ms`
- Per-session aggregate summaries (total calls, tokens, latency)

Additional logged events:
- **Session lifecycle** — create, update, delete, evict (with TTL reason)
- **Pipeline stages** — stage timing, success/error status per stage
- **Guardrail triggers** — iteration limits, prompt injection attempts
- **External API calls** — Adzuna and Tavily requests with timing and result counts

### Session Management

Sessions are automatically evicted after **1 hour of inactivity**. A background reaper task runs every 60 seconds to clean up expired sessions and free resources.

### Health Check

`GET /api/health` returns:
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

### CloudWatch (Production)

In production, Docker containers stream logs directly to CloudWatch via the `awslogs` driver — no agent installation required.

**Log Groups:**
- `/jobaid/backend` — API requests, LLM calls, agent execution
- `/jobaid/frontend` — nginx access/error logs

**Alarms:**
- Instance status check (auto-recovers on failure)
- High CPU (>80% for 5 minutes)

**Dashboard** (`jobaid-dashboard`) — 22 widgets across 5 groups:
- **Infrastructure** — EC2 CPU utilization, network I/O
- **API health** — request throughput, error rate (4xx/5xx), latency percentiles (p50/p90/p99), slowest endpoints, recent error details
- **LLM metrics** — token usage over time, cost by task type, call errors, latency by agent, session summaries
- **Pipeline & External** — stage timing and latency, Adzuna/Tavily health, latency, and result counts
- **Operations** — session activity over time, session funnel, guardrail triggers

**Useful CloudWatch Logs Insights queries:**

```
# Error rate in last hour
fields @timestamp, @message | filter @message like /ERROR/ | stats count() by bin(5m)

# LLM call latency
fields @timestamp, model, latency_ms | filter @message like /llm_call/

# Slow API requests (>5s)
fields method, path, duration | filter duration > 5
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
- **tavily-python** — Tavily web search API (courses, trends, salary, company research)
- **beautifulsoup4** — HTML parsing
- **pypdf** — PDF resume parsing
- **python-docx** — DOCX resume parsing
- **python-dotenv** — environment variable management

### Frontend (Node.js 24+)

- **Angular 20** — standalone components, signals, control flow syntax
- **Angular Material 20** — Material 3 design components (toolbar, cards, chips, stepper, expansion panels)
- **marked** — Markdown rendering for summary reports
- **RxJS** — polling pipeline status with `interval` + `switchMap`
- **TypeScript 5.9** — strict mode

## Credits

Developed for NUS-ISS Practice Module
Authors: Sanath, Anastasia, Hany, Vincent (Team 31)

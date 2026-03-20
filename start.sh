#!/bin/bash
# JobAId — Start script with preflight checks
# Usage: ./start.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "  ${GREEN}✓${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; }
warn() { echo -e "  ${YELLOW}!${NC} $1"; }

echo ""
echo "========================================="
echo "  JobAId — Preflight Check"
echo "========================================="
echo ""

ERRORS=0

# --- 1. Check we're in the right directory ---
echo "1. Project directory"
if [ -f "pyproject.toml" ] && [ -d "agents" ] && [ -d "frontend" ]; then
    pass "In JobAId project root"
else
    fail "Not in JobAId project root. Run this from the project directory."
    exit 1
fi

# --- 2. Check Python ---
echo "2. Python"
if command -v python3 &>/dev/null; then
    PY_VERSION=$(python3 --version 2>&1)
    pass "$PY_VERSION"
else
    fail "python3 not found"
    ERRORS=$((ERRORS + 1))
fi

# --- 3. Check Node.js ---
echo "3. Node.js"
if command -v node &>/dev/null; then
    NODE_VERSION=$(node --version 2>&1)
    pass "Node $NODE_VERSION"
else
    fail "node not found — needed for frontend"
    ERRORS=$((ERRORS + 1))
fi

# --- 4. Check .env file ---
echo "4. Environment variables"
if [ -f ".env" ]; then
    pass ".env file exists"
else
    if [ -f ".env.example" ]; then
        warn ".env not found — copying from .env.example"
        cp .env.example .env
        warn "Please edit .env with your API keys"
    else
        fail ".env not found and no .env.example to copy"
    fi
fi

# Check required keys
if [ -f ".env" ]; then
    source_env() {
        while IFS='=' read -r key value; do
            key=$(echo "$key" | xargs)
            [[ "$key" =~ ^#.*$ ]] && continue
            [[ -z "$key" ]] && continue
            value=$(echo "$value" | xargs)
            export "$key=$value" 2>/dev/null
        done < .env
    }
    source_env
fi

# OPENAI_API_KEY — required
if [ -n "$OPENAI_API_KEY" ] && [ "$OPENAI_API_KEY" != "your_openai_api_key_here" ]; then
    pass "OPENAI_API_KEY is set"
else
    fail "OPENAI_API_KEY not set — LLM calls will fail!"
    echo "       Get one at: https://platform.openai.com/api-keys"
    ERRORS=$((ERRORS + 1))
fi

# ADZUNA — optional but recommended
if [ -n "$ADZUNA_APP_ID" ] && [ "$ADZUNA_APP_ID" != "your_adzuna_app_id" ]; then
    pass "ADZUNA_APP_ID is set (real job search)"
else
    warn "ADZUNA_APP_ID not set — will use mock job data"
    echo "       Get one at: https://developer.adzuna.com/"
fi

if [ -n "$ADZUNA_API_KEY" ] && [ "$ADZUNA_API_KEY" != "your_adzuna_api_key" ]; then
    pass "ADZUNA_API_KEY is set"
else
    warn "ADZUNA_API_KEY not set"
fi

# TAVILY — optional but recommended
if [ -n "$TAVILY_API_KEY" ] && [ "$TAVILY_API_KEY" != "your_tavily_api_key" ]; then
    pass "TAVILY_API_KEY is set (web search for courses/trends)"
else
    warn "TAVILY_API_KEY not set — will use seed data only"
    echo "       Get one at: https://tavily.com/"
fi

# --- 5. Check Python dependencies ---
echo "5. Python dependencies"
if [ -d ".venv" ]; then
    pass ".venv exists"
    PIP=".venv/bin/pip"
    PYTHON=".venv/bin/python"
else
    warn ".venv not found — creating virtual environment..."
    python3 -m venv .venv
    pass ".venv created"
    PIP=".venv/bin/pip"
    PYTHON=".venv/bin/python"
fi

# Check if key packages are installed
if $PYTHON -c "import langchain, fastapi, chromadb" 2>/dev/null; then
    pass "Key Python packages installed"
else
    warn "Installing Python dependencies..."
    if command -v uv &>/dev/null; then
        uv sync 2>&1 | tail -3
    else
        $PIP install "langchain>=0.3.27,<0.4" "langchain-openai>=0.2.14,<0.3" \
            "langgraph>=0.6.6,<0.7" chromadb fastapi pydantic-settings httpx \
            tavily-python pypdf python-docx beautifulsoup4 python-multipart \
            uvicorn 2>&1 | tail -3
    fi
    pass "Python dependencies installed"
fi

# --- 6. Check frontend dependencies ---
echo "6. Frontend dependencies"
if [ -d "frontend/node_modules" ]; then
    pass "node_modules exists"
else
    warn "Installing frontend dependencies..."
    cd frontend && npm install 2>&1 | tail -3 && cd ..
    pass "Frontend dependencies installed"
fi

# --- 7. Run tests ---
echo "7. Running tests"
TEST_OUTPUT=$(PYTHONPATH=. $PYTHON -m pytest tests/ -q --tb=line 2>&1)
TEST_RESULT=$(echo "$TEST_OUTPUT" | tail -1)
if echo "$TEST_RESULT" | grep -q "passed"; then
    pass "$TEST_RESULT"
else
    fail "Tests failed:"
    echo "$TEST_OUTPUT" | tail -5
    ERRORS=$((ERRORS + 1))
fi

# --- 8. Check ports ---
echo "8. Port availability"
if lsof -ti:8000 &>/dev/null; then
    warn "Port 8000 in use — killing existing process"
    kill $(lsof -ti:8000) 2>/dev/null
    sleep 1
fi
pass "Port 8000 available (backend)"

if lsof -ti:4200 &>/dev/null; then
    warn "Port 4200 in use — killing existing process"
    kill $(lsof -ti:4200) 2>/dev/null
    sleep 1
fi
pass "Port 4200 available (frontend)"

# --- Summary ---
echo ""
echo "========================================="
if [ $ERRORS -gt 0 ]; then
    echo -e "  ${RED}PREFLIGHT FAILED — $ERRORS error(s)${NC}"
    echo "  Fix the errors above and run again."
    echo "========================================="
    exit 1
fi
echo -e "  ${GREEN}ALL CHECKS PASSED${NC}"
echo "========================================="
echo ""

# --- Start servers ---
echo "Starting backend on http://localhost:8000 ..."
PYTHONPATH=. nohup $PYTHON -m uvicorn api.app:app --host 0.0.0.0 --port 8000 > /tmp/jobaid_backend.log 2>&1 &
BACKEND_PID=$!
disown $BACKEND_PID 2>/dev/null
sleep 3

# Verify backend started
if curl -s http://localhost:8000/api/health | grep -q "healthy"; then
    pass "Backend running (PID $BACKEND_PID)"
else
    fail "Backend failed to start. Check /tmp/jobaid_backend.log"
    exit 1
fi

echo "Starting frontend on http://localhost:4200 ..."
cd frontend
nohup npx ng serve --host 0.0.0.0 --port 4200 > /tmp/jobaid_frontend.log 2>&1 &
FRONTEND_PID=$!
disown $FRONTEND_PID 2>/dev/null
cd ..

echo ""
echo "  Waiting for frontend to build..."
for i in $(seq 1 30); do
    if curl -s -o /dev/null -w '' http://localhost:4200 2>/dev/null; then
        pass "Frontend running (PID $FRONTEND_PID)"
        break
    fi
    sleep 1
done

echo ""
echo "========================================="
echo -e "  ${GREEN}JobAId is running!${NC}"
echo ""
echo "  Frontend:  http://localhost:4200"
echo "  Backend:   http://localhost:8000"
echo "  API docs:  http://localhost:8000/docs"
echo "  Health:    http://localhost:8000/api/health"
echo ""
echo "  Logs:"
echo "    Backend:  tail -f /tmp/jobaid_backend.log"
echo "    Frontend: tail -f /tmp/jobaid_frontend.log"
echo ""
echo "  To stop:   kill $BACKEND_PID $FRONTEND_PID"
echo "========================================="

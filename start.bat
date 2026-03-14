@echo off
REM JobAId — Start script with preflight checks (Windows)
REM Usage: start.bat

setlocal enabledelayedexpansion

echo.
echo =========================================
echo   JobAId — Preflight Check
echo =========================================
echo.

set ERRORS=0

REM --- 1. Check we're in the right directory ---
echo 1. Project directory
if exist "pyproject.toml" if exist "agents" if exist "frontend" (
    echo   [OK] In JobAId project root
) else (
    echo   [FAIL] Not in JobAId project root. Run this from the project directory.
    exit /b 1
)

REM --- 2. Check Python ---
echo 2. Python
python --version >nul 2>&1
if %errorlevel%==0 (
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo   [OK] %%i
) else (
    python3 --version >nul 2>&1
    if %errorlevel%==0 (
        for /f "tokens=*" %%i in ('python3 --version 2^>^&1') do echo   [OK] %%i
    ) else (
        echo   [FAIL] Python not found
        set /a ERRORS+=1
    )
)

REM --- 3. Check Node.js ---
echo 3. Node.js
node --version >nul 2>&1
if %errorlevel%==0 (
    for /f "tokens=*" %%i in ('node --version 2^>^&1') do echo   [OK] Node %%i
) else (
    echo   [FAIL] Node.js not found — needed for frontend
    set /a ERRORS+=1
)

REM --- 4. Check .env file ---
echo 4. Environment variables
if exist ".env" (
    echo   [OK] .env file exists
) else (
    if exist ".env.example" (
        echo   [WARN] .env not found — copying from .env.example
        copy .env.example .env >nul
        echo   [WARN] Please edit .env with your API keys!
    ) else (
        echo   [FAIL] .env not found
    )
)

REM Load .env
if exist ".env" (
    for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
        set "line=%%a"
        if not "!line:~0,1!"=="#" (
            if not "%%a"=="" (
                set "%%a=%%b"
            )
        )
    )
)

REM Check required keys
if defined OPENAI_API_KEY (
    if not "%OPENAI_API_KEY%"=="your_openai_api_key_here" (
        echo   [OK] OPENAI_API_KEY is set
    ) else (
        echo   [FAIL] OPENAI_API_KEY is placeholder — edit .env!
        echo          Get one at: https://platform.openai.com/api-keys
        set /a ERRORS+=1
    )
) else (
    echo   [FAIL] OPENAI_API_KEY not set — LLM calls will fail!
    echo          Get one at: https://platform.openai.com/api-keys
    set /a ERRORS+=1
)

if defined ADZUNA_APP_ID (
    echo   [OK] ADZUNA_APP_ID is set ^(real job search^)
) else (
    echo   [WARN] ADZUNA_APP_ID not set — will use mock job data
    echo          Get one at: https://developer.adzuna.com/
)

if defined ADZUNA_API_KEY (
    echo   [OK] ADZUNA_API_KEY is set
) else (
    echo   [WARN] ADZUNA_API_KEY not set
)

if defined TAVILY_API_KEY (
    echo   [OK] TAVILY_API_KEY is set ^(web search^)
) else (
    echo   [WARN] TAVILY_API_KEY not set — will use seed data only
    echo          Get one at: https://tavily.com/
)

REM --- 5. Check Python dependencies ---
echo 5. Python dependencies
if exist ".venv" (
    echo   [OK] .venv exists
) else (
    echo   [WARN] Creating virtual environment...
    python -m venv .venv
    echo   [OK] .venv created
)

REM Check if key packages are installed
.venv\Scripts\python -c "import langchain, fastapi, chromadb" >nul 2>&1
if %errorlevel%==0 (
    echo   [OK] Key Python packages installed
) else (
    echo   [WARN] Installing Python dependencies...
    where uv >nul 2>&1
    if %errorlevel%==0 (
        uv sync
    ) else (
        .venv\Scripts\pip install "langchain>=0.3.27,<0.4" "langchain-openai>=0.2.14,<0.3" "langgraph>=0.6.6,<0.7" chromadb fastapi pydantic-settings httpx tavily-python pypdf python-docx beautifulsoup4 python-multipart uvicorn pytest
    )
    echo   [OK] Dependencies installed
)

REM --- 6. Check frontend dependencies ---
echo 6. Frontend dependencies
if exist "frontend\node_modules" (
    echo   [OK] node_modules exists
) else (
    echo   [WARN] Installing frontend dependencies...
    cd frontend
    call npm install
    cd ..
    echo   [OK] Frontend dependencies installed
)

REM --- 7. Run tests ---
echo 7. Running tests (output saved to test_results.txt)
.venv\Scripts\python -c "import pytest" >nul 2>&1
if not %errorlevel%==0 (
    echo   [WARN] pytest not installed — installing...
    .venv\Scripts\pip install pytest >nul 2>&1
)
set PYTHONPATH=.
.venv\Scripts\python -m pytest tests/ -v --tb=short > test_results.txt 2>&1
type test_results.txt | findstr /C:"passed"
if %errorlevel%==0 (
    echo   [OK] Tests passed — see test_results.txt for details
) else (
    echo   [FAIL] Some tests failed — check test_results.txt
    echo.
    echo   Failed tests:
    type test_results.txt | findstr /C:"FAILED"
    echo.
    set /a ERRORS+=1
)

REM --- Summary ---
echo.
echo =========================================
if %ERRORS% gtr 0 (
    echo   PREFLIGHT FAILED — %ERRORS% error^(s^)
    echo   Fix the errors above and run again.
    echo =========================================
    pause
    exit /b 1
)
echo   ALL CHECKS PASSED
echo =========================================
echo.

REM --- Kill existing processes on our ports ---
for /f "tokens=5" %%p in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do taskkill /PID %%p /F >nul 2>&1
for /f "tokens=5" %%p in ('netstat -aon ^| findstr :4200 ^| findstr LISTENING') do taskkill /PID %%p /F >nul 2>&1
timeout /t 2 /nobreak >nul

REM --- Start backend ---
echo Starting backend on http://localhost:8000 ...
set PYTHONPATH=.
start "JobAId-Backend" /min .venv\Scripts\python -m uvicorn api.app:app --host 0.0.0.0 --port 8000
timeout /t 4 /nobreak >nul

REM Verify backend
curl -s http://localhost:8000/api/health | findstr "healthy" >nul 2>&1
if %errorlevel%==0 (
    echo   [OK] Backend running
) else (
    echo   [FAIL] Backend failed to start
    pause
    exit /b 1
)

REM --- Start frontend ---
echo Starting frontend on http://localhost:4200 ...
cd frontend
start "JobAId-Frontend" /min cmd /c "npx ng serve --host 0.0.0.0 --port 4200"
cd ..

echo.
echo   Waiting for frontend to build...
timeout /t 15 /nobreak >nul

echo.
echo =========================================
echo   JobAId is running!
echo.
echo   Frontend:  http://localhost:4200
echo   Backend:   http://localhost:8000
echo   API docs:  http://localhost:8000/docs
echo   Health:    http://localhost:8000/api/health
echo.
echo   Both servers are running in minimized
echo   windows. Close them to stop.
echo =========================================
echo.

REM Open browser
start http://localhost:4200

pause

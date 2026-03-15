@echo off
REM JobAId — Quick Start (Windows)
REM Double-click this file or run: start.bat

setlocal enabledelayedexpansion

echo.
echo =========================================
echo   JobAId — Starting Up
echo =========================================
echo.

REM --- Check we're in the right place ---
if not exist "pyproject.toml" (
    echo [FAIL] Run this from the JobAId project folder!
    pause
    exit /b 1
)
echo [OK] Project directory

REM --- Check Python ---
python --version >nul 2>&1
if not %errorlevel%==0 (
    echo [FAIL] Python not found. Install from python.org
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo [OK] %%i

REM --- Check Node ---
node --version >nul 2>&1
if not %errorlevel%==0 (
    echo [FAIL] Node.js not found. Install from nodejs.org
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('node --version 2^>^&1') do echo [OK] Node %%i

REM --- Check .env ---
if not exist ".env" (
    echo.
    echo [FAIL] No .env file found!
    echo.
    echo   Create a file called .env in this folder with:
    echo.
    echo   OPENAI_API_KEY=your-key-here
    echo   TAVILY_API_KEY=your-key-here
    echo   ADZUNA_APP_ID=your-id-here
    echo   ADZUNA_API_KEY=your-key-here
    echo.
    pause
    exit /b 1
)
echo [OK] .env file found

REM --- Load .env into environment ---
for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
    set "line=%%a"
    if not "!line:~0,1!"=="#" (
        if not "%%a"=="" set "%%a=%%b"
    )
)

if not defined OPENAI_API_KEY (
    echo [FAIL] OPENAI_API_KEY not in .env — the app needs this!
    pause
    exit /b 1
)
echo [OK] OPENAI_API_KEY loaded

REM --- Install Python packages (skip if already done) ---
echo.
echo Checking Python packages...
python -c "import langchain, fastapi, chromadb" >nul 2>&1
if not %errorlevel%==0 (
    echo Installing Python dependencies ^(one-time, may take a minute^)...
    pip install "langchain>=0.3.27,<0.4" "langchain-openai>=0.2.14,<0.3" "langgraph>=0.6.6,<0.7" chromadb fastapi pydantic-settings httpx tavily-python pypdf python-docx beautifulsoup4 python-multipart uvicorn
    if not %errorlevel%==0 (
        echo [FAIL] pip install failed
        pause
        exit /b 1
    )
)
echo [OK] Python packages ready

REM --- Install frontend packages ---
if not exist "frontend\node_modules" (
    echo Installing frontend dependencies ^(one-time^)...
    cd frontend
    call npm install
    cd ..
)
echo [OK] Frontend packages ready

REM --- Kill anything on our ports ---
echo.
echo Clearing ports...
for /f "tokens=5" %%p in ('netstat -aon 2^>nul ^| findstr :8000 ^| findstr LISTENING') do taskkill /PID %%p /F >nul 2>&1
for /f "tokens=5" %%p in ('netstat -aon 2^>nul ^| findstr :4200 ^| findstr LISTENING') do taskkill /PID %%p /F >nul 2>&1
timeout /t 2 /nobreak >nul

REM --- Start backend ---
echo.
echo Starting backend...
set PYTHONPATH=.
start "JobAId-Backend" cmd /k "set PYTHONPATH=. && for /f "usebackq tokens=1,* delims==" %%a in (".env") do (set "%%a=%%b") && python -m uvicorn api.app:app --host 0.0.0.0 --port 8000"

echo   Waiting for backend...
timeout /t 5 /nobreak >nul

REM --- Verify backend ---
curl -s http://localhost:8000/api/health >nul 2>&1
if %errorlevel%==0 (
    echo [OK] Backend running on http://localhost:8000
) else (
    echo [WARN] Backend may still be starting — give it a few more seconds
)

REM --- Start frontend ---
echo.
echo Starting frontend ^(takes ~15 seconds to build^)...
cd frontend
start "JobAId-Frontend" cmd /k "npx ng serve --host 0.0.0.0 --port 4200"
cd ..

echo.
echo =========================================
echo.
echo   Both servers are starting!
echo.
echo   Backend:   http://localhost:8000
echo   Frontend:  http://localhost:4200  ^(wait for build^)
echo   Health:    http://localhost:8000/api/health
echo.
echo   Two new windows opened — keep them running.
echo   Close them when you're done.
echo.
echo   Opening browser in 20 seconds...
echo.
echo =========================================

timeout /t 20 /nobreak >nul
start http://localhost:4200

pause

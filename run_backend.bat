@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
    set "line=%%a"
    if not "!line:~0,1!"=="#" (
        if not "%%a"=="" set "%%a=%%b"
    )
)
set PYTHONPATH=.
python -m uvicorn api.app:app --host 0.0.0.0 --port 8000

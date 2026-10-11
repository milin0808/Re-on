@echo off
setlocal
cd /d "%~dp0"
echo [RE:ON] Starting Memory Engine...
if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv 2>nul
  if errorlevel 1 python -m venv .venv
  if errorlevel 1 (
    echo Python 3.10+ is required. Check installation / PATH.
    pause
    exit /b 1
  )
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo Dependency installation failed. Check Internet connection.
  pause
  exit /b 1
)
echo.
echo API Docs: http://127.0.0.1:8000/docs
echo Keep this window open while using the API.
echo.
".venv\Scripts\python.exe" -m uvicorn api:app --host 127.0.0.1 --port 8000
pause

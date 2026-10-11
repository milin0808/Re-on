@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" try_api.py
) else (
  py -3 try_api.py 2>nul
  if errorlevel 1 python try_api.py
)
pause

@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  py -3 main.py --input data\sample_moments.json --output outputs\memories.json
) else (
  python main.py --input data\sample_moments.json --output outputs\memories.json
)
echo.
echo Finished. Check outputs\memories.json
pause

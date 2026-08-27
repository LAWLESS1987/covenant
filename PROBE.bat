@echo off
REM ============================================================
REM  Finds which AI judges actually work from THIS machine.
REM  Run in Windows (not WSL) -- Ollama listens on the Windows
REM  side, and WSL has its own network namespace so localhost
REM  there is not the same localhost.
REM ============================================================
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"

echo.
echo Probing every judge endpoint with one real call each...
echo (local Ollama models first, then hosted providers)
echo.

python judge_probe.py

echo.
echo ============================================================
echo  Copy everything above and paste it to Claude.
echo ============================================================
pause
endlocal

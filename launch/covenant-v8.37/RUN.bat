@echo off
REM ============================================================
REM  ONE double-click. Runs everything that needs no API key,
REM  and prints one block to paste back.
REM  Run in Windows, not WSL (Ollama lives on the Windows side).
REM ============================================================
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"

set COVENANT_LOCAL_JUDGE_URL=http://localhost:11434/v1/chat/completions
set COVENANT_LOCAL_JUDGE_MODEL=qwen3.6:latest
set COVENANT_LOCAL_JUDGE_TIMEOUT=300
set COVENANT_JUDGE_PROVIDERS=local,mock
set COVENANT_INSECURE_MOCK_JUDGE=1

echo ############ 1 of 3  PORTFOLIO ############
python daily.py

echo.
echo ############ 2 of 3  JUDGE ############
python judge_check.py

echo.
echo ############ 3 of 3  OTHER JUDGES ############
python judge_probe.py --ollama-only

echo.
echo ============================================================
echo  Select all ^(right-click ^> Select All^), copy, paste to Claude.
echo ============================================================
pause
endlocal

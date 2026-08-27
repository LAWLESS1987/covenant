@echo off
REM ============================================================
REM  Judge check -- uses the qwen3.6 model already on this PC.
REM  No API key. No internet needed. Run in Windows, not WSL:
REM  Ollama listens on the Windows side and WSL has its own
REM  network namespace, so localhost there is a different host.
REM ============================================================
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"

set COVENANT_LOCAL_JUDGE_URL=http://localhost:11434/v1/chat/completions
set COVENANT_LOCAL_JUDGE_MODEL=qwen3.6:latest
set COVENANT_LOCAL_JUDGE_TIMEOUT=300
set COVENANT_JUDGE_PROVIDERS=local,mock
set COVENANT_INSECURE_MOCK_JUDGE=1

echo.
echo Asking qwen3.6 to judge two test transactions.
echo A big model on CPU can take a minute or two. Let it run.
echo.

python judge_check.py

echo.
echo ============================================================
echo  Paste the above to Claude.
echo ============================================================
pause
endlocal

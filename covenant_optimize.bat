@echo off
REM ============================================================================
REM  covenant_optimize.bat -- one hill-climbing round over the judge config.
REM
REM  Each run starts from judge_config.json, which is the winner of the last
REM  run. covenant_judge_ollama.py reads that file at runtime, so an accepted
REM  change reaches the live nodes on their next restart.
REM
REM  A candidate is accepted only if it is CHEAPER *and* still meets every
REM  per-category threshold on the full 37-case suite. Cost never buys
REM  correctness.
REM
REM  Safe to run while the nodes are up: it only talks to Ollama, never to a
REM  node, and writes nothing to the chain. It will compete for CPU with any
REM  verdict in flight, so avoid submitting transactions while it runs.
REM ============================================================================
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"
set COVENANT_LOCAL_JUDGE_URL=http://127.0.0.1:11434/v1/chat/completions
if "%COVENANT_LOCAL_JUDGE_MODEL%"=="" set COVENANT_LOCAL_JUDGE_MODEL=qwen3:8b
set COVENANT_LOCAL_JUDGE_TIMEOUT=600

python covenant_optimize.py --rounds %1 2>&1
if "%1"=="" python covenant_optimize.py --rounds 1 2>&1

echo.
echo ============================================================
echo  judge_config.json holds the winner. optimize_log.jsonl
echo  holds every round including the rejections - a search that
echo  only records its wins cannot tell you it has stopped
echo  finding any.
echo.
echo  Apply to the running nodes:
echo     covenant_prod.bat stop  ^&^&  covenant_prod.bat
echo ============================================================
pause
endlocal

@echo off
REM ===========================================================================
REM  AG_LEAN_MEASURE.bat -- 2026-08-22. Measures what the running system costs
REM  on THIS box before anything is tuned. Changes nothing: it reads memory,
REM  what Ollama holds resident, the server-side env actually in force, the
REM  power plan, the judge anomaly counts on both nodes, and then runs
REM  judge_bench.py twice -- once at prod's num_predict=96 and once at the 160
REM  that OLLAMA_TUNING.md says is the measured floor for a complete verdict.
REM  Output: LEAN_MEASURE.txt. No parenthesised blocks -- GOTO only.
REM ===========================================================================
setlocal
cd /d "%~dp0"
set OUT=LEAN_MEASURE.txt
set PY=python
if exist ".venv\Scripts\python.exe" set PY=.venv\Scripts\python.exe

> "%OUT%" echo ==== lean measure %DATE% %TIME% ====
>> "%OUT%" echo.
>> "%OUT%" echo --- physical memory, KB ---
wmic OS get FreePhysicalMemory,TotalVisibleMemorySize /format:list 2>nul | findstr /r "." >> "%OUT%"
>> "%OUT%" echo.
>> "%OUT%" echo --- processes ---
tasklist /fi "imagename eq ollama.exe" >> "%OUT%" 2>&1
tasklist /fi "imagename eq python.exe" >> "%OUT%" 2>&1
tasklist /fi "imagename eq python3.12.exe" >> "%OUT%" 2>&1
>> "%OUT%" echo.
>> "%OUT%" echo --- what ollama holds resident right now ---
ollama ps >> "%OUT%" 2>&1
>> "%OUT%" echo.
>> "%OUT%" echo --- server-side OLLAMA_* actually in force ---
set OLLAMA >> "%OUT%" 2>&1
>> "%OUT%" echo.
>> "%OUT%" echo --- power plan ---
powercfg /getactivescheme >> "%OUT%" 2>&1
>> "%OUT%" echo.
>> "%OUT%" echo --- judge-related anomalies, node A then B ---
curl -s -m 8 http://127.0.0.1:5000/anomalies >> "%OUT%" 2>&1
>> "%OUT%" echo.
curl -s -m 8 http://127.0.0.1:5020/anomalies >> "%OUT%" 2>&1
>> "%OUT%" echo.

set COVENANT_LOCAL_JUDGE_URL=http://127.0.0.1:11434/v1/chat/completions
set COVENANT_LOCAL_JUDGE_MODEL=qwen3:8b
set COVENANT_LOCAL_JUDGE_TIMEOUT=300
set COVENANT_JUDGE_PROVIDERS=local
set COVENANT_OLLAMA_NUM_CTX=2048
set COVENANT_OLLAMA_KEEP_ALIVE=30m

>> "%OUT%" echo --- bench A: num_predict=96, what production sends ---
set COVENANT_OLLAMA_NUM_PREDICT=96
"%PY%" judge_bench.py --quick >> "%OUT%" 2>&1
>> "%OUT%" echo.
>> "%OUT%" echo --- bench B: num_predict=160, what OLLAMA_TUNING.md measured ---
set COVENANT_OLLAMA_NUM_PREDICT=160
"%PY%" judge_bench.py --quick >> "%OUT%" 2>&1
>> "%OUT%" echo.
>> "%OUT%" echo ==== DONE %DATE% %TIME% ====
type "%OUT%"
echo.
echo Finished -- LEAN_MEASURE.txt written. Nothing was changed.
pause
endlocal

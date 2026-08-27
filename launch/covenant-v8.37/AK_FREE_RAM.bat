@echo off
REM ===========================================================================
REM  AK_FREE_RAM.bat -- unload the judge model. 2026-08-22.
REM
REM  llama-server.exe holds 5,234 MB -- by far the largest single thing on this
REM  box, and it is held even when the chain is idle because the node sends
REM  keep_alive=60m on every verdict. The chain is at height 3 with no pending
REM  transactions, so nothing needs it resident right now.
REM
REM  COST, stated plainly: the next verdict pays a cold load. Measured today,
REM  same six-case bench: first verdict after a cold start 39.9s, warm 12.1s.
REM  So about 28 seconds, once, on the next transaction. Nothing is lost.
REM
REM  Touches no node, no database, no setting. `ollama ps` after shows empty.
REM ===========================================================================
setlocal
cd /d "%~dp0"
set OUT=FREE_RAM.txt
set PY=python
if exist ".venv\Scripts\python.exe" set PY=.venv\Scripts\python.exe

> "%OUT%" echo ==== free ram %DATE% %TIME% ====
>> "%OUT%" echo --- before ---
"%SystemRoot%\System32\wbem\wmic.exe" OS get FreePhysicalMemory /format:list 2>nul | findstr /r "." >> "%OUT%"
>> "%OUT%" echo --- loaded models before ---
ollama ps >> "%OUT%" 2>&1
>> "%OUT%" echo.
>> "%OUT%" echo --- unloading qwen3:8b ---
ollama stop qwen3:8b >> "%OUT%" 2>&1
timeout /t 5 /nobreak >nul
>> "%OUT%" echo --- loaded models after ---
ollama ps >> "%OUT%" 2>&1
>> "%OUT%" echo.
>> "%OUT%" echo --- after ---
"%SystemRoot%\System32\wbem\wmic.exe" OS get FreePhysicalMemory /format:list 2>nul | findstr /r "." >> "%OUT%"
>> "%OUT%" echo.
>> "%OUT%" echo --- top consumers now ---
"%PY%" topmem.py >> "%OUT%" 2>&1
>> "%OUT%" echo ==== DONE ====
type "%OUT%"
echo.
pause
endlocal

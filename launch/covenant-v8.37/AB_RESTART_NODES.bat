@echo off
REM ===========================================================================
REM  AB_RESTART_NODES.bat -- written 2026-08-22 (L-started session)
REM
REM  WHY THIS EXISTS. covenant_prod.bat's "stop" runs
REM      taskkill /fi "windowtitle eq Covenant Node A*" /f
REM  which kills the CMD WRAPPER window, not the python.exe it launched. The
REM  node keeps listening on 5000/5020, so the very next start says "node A
REM  already up" and does nothing -- observed live at 14:12 today. That is a
REM  mechanism by which this machine can run a source from days ago while
REM  every restart reports success.
REM
REM  This stops by PORT as well as by title, proves the ports are free, then
REM  hands over to covenant_prod.bat, which is still the thing that knows how
REM  to start a node. It never deletes a database.
REM
REM  Output: NODE_RESTART.txt
REM ===========================================================================
setlocal EnableDelayedExpansion
cd /d "%~dp0"
set OUT=NODE_RESTART.txt

REM ---------------------------------------------------------------------------
REM  P17 GUARD, added 2026-08-26. READ THIS BEFORE REMOVING IT.
REM
REM  This script's stop ALWAYS succeeds. covenant_prod.bat's start CAN refuse:
REM  its first act is to curl Ollama on 11434 and abort if nothing answers,
REM  which is correct, because a judge that cannot be reached fails CLOSED and
REM  a node in that state rejects every transaction while looking healthy.
REM
REM  Composed, that is not a restart. It is a stop. A machine that was serving
REM  a chain a minute ago serves nothing, and the only notice is a line in a
REM  console that scrolls past. The judge is a 5.2 GB local model on a box
REM  P12 measured at ~3.5 GB free, so "Ollama is not answering right now" is
REM  an ordinary state, not an exotic one.
REM
REM  So: ask FIRST, and refuse to stop what cannot be started. This can only
REM  ever decline to act -- it never starts, kills or changes anything.
REM ---------------------------------------------------------------------------
echo Checking the ethics judge is reachable BEFORE stopping anything ...
curl -s -m 8 http://127.0.0.1:11434/api/tags >nul 2>nul
if %errorlevel% neq 0 goto NO_JUDGE
echo   Ollama answers on 11434. Safe to restart.
goto JUDGE_OK

:NO_JUDGE
echo.
echo   REFUSING TO RESTART. Ollama is not answering on 11434.
echo.
echo   covenant_prod.bat would abort before starting the nodes, so stopping
echo   them now would take the chain down and leave it down. Nothing has
echo   been stopped. The nodes are still running whatever they were running.
echo.
echo   Start Ollama, confirm with:  curl http://127.0.0.1:11434/api/tags
echo   then run this again.
echo.
> "NODE_RESTART.txt" echo ==== node restart REFUSED %DATE% %TIME% ====
>> "NODE_RESTART.txt" echo P17: Ollama not answering on 11434; stop would not be followed by a start.
>> "NODE_RESTART.txt" echo Nothing was stopped. No database was touched.
pause
exit /b 3

:JUDGE_OK

> "%OUT%" echo ==== node restart  %DATE% %TIME% ====
>> "%OUT%" echo.
>> "%OUT%" echo --- BEFORE: health A ---
curl -s -m 8 http://127.0.0.1:5000/health >> "%OUT%" 2>&1
>> "%OUT%" echo.
>> "%OUT%" echo --- BEFORE: health B ---
curl -s -m 8 http://127.0.0.1:5020/health >> "%OUT%" 2>&1
>> "%OUT%" echo.
>> "%OUT%" echo --- who is listening ---
netstat -ano | findstr /r /c:":5000 .*LISTENING" >> "%OUT%" 2>&1
netstat -ano | findstr /r /c:":5020 .*LISTENING" >> "%OUT%" 2>&1

>> "%OUT%" echo.
>> "%OUT%" echo --- stop by window title, whole tree ---
taskkill /f /t /fi "windowtitle eq Covenant Node A*" >> "%OUT%" 2>&1
taskkill /f /t /fi "windowtitle eq Covenant Node B*" >> "%OUT%" 2>&1
taskkill /f /t /fi "windowtitle eq Covenant Watchdog*" >> "%OUT%" 2>&1
timeout /t 4 /nobreak >nul

>> "%OUT%" echo --- stop by port, whatever still holds 5000 or 5020 ---
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /r /c:":5000 .*LISTENING"') do taskkill /f /pid %%p >> "%OUT%" 2>&1
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /r /c:":5020 .*LISTENING"') do taskkill /f /pid %%p >> "%OUT%" 2>&1
timeout /t 4 /nobreak >nul

>> "%OUT%" echo.
>> "%OUT%" echo --- ports after stop, expect nothing listed ---
netstat -ano | findstr /r /c:":5000 .*LISTENING" >> "%OUT%" 2>&1
netstat -ano | findstr /r /c:":5020 .*LISTENING" >> "%OUT%" 2>&1

>> "%OUT%" echo.
>> "%OUT%" echo --- start on the deployed source ---
call covenant_prod.bat >> "%OUT%" 2>&1
timeout /t 25 /nobreak >nul

>> "%OUT%" echo.
>> "%OUT%" echo --- AFTER: health A ---
curl -s -m 10 http://127.0.0.1:5000/health >> "%OUT%" 2>&1
>> "%OUT%" echo.
>> "%OUT%" echo --- AFTER: health B ---
curl -s -m 10 http://127.0.0.1:5020/health >> "%OUT%" 2>&1
>> "%OUT%" echo.
>> "%OUT%" echo ==== DONE %DATE% %TIME% ====
type "%OUT%"
echo.
pause
endlocal

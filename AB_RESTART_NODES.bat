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
>> "%OUT%" echo --- BEFORE: health C ---
curl -s -m 8 http://127.0.0.1:5060/health >> "%OUT%" 2>&1
>> "%OUT%" echo.
>> "%OUT%" echo --- who is listening ---
netstat -ano | findstr /r /c:":5000 .*LISTENING" >> "%OUT%" 2>&1
netstat -ano | findstr /r /c:":5020 .*LISTENING" >> "%OUT%" 2>&1
netstat -ano | findstr /r /c:":5060 .*LISTENING" >> "%OUT%" 2>&1

>> "%OUT%" echo.
>> "%OUT%" echo --- stop by window title, whole tree ---
taskkill /f /t /fi "windowtitle eq Covenant Node A*" >> "%OUT%" 2>&1
taskkill /f /t /fi "windowtitle eq Covenant Node B*" >> "%OUT%" 2>&1
taskkill /f /t /fi "windowtitle eq Covenant Node C*" >> "%OUT%" 2>&1
taskkill /f /t /fi "windowtitle eq Covenant Watchdog*" >> "%OUT%" 2>&1
timeout /t 4 /nobreak >nul

>> "%OUT%" echo --- stop by port, whatever still holds 5000 or 5020 ---
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /r /c:":5000 .*LISTENING"') do taskkill /f /pid %%p >> "%OUT%" 2>&1
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /r /c:":5020 .*LISTENING"') do taskkill /f /pid %%p >> "%OUT%" 2>&1
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /r /c:":5060 .*LISTENING"') do taskkill /f /pid %%p >> "%OUT%" 2>&1
timeout /t 4 /nobreak >nul

>> "%OUT%" echo.
>> "%OUT%" echo --- ports after stop, expect nothing listed ---
netstat -ano | findstr /r /c:":5000 .*LISTENING" >> "%OUT%" 2>&1
netstat -ano | findstr /r /c:":5020 .*LISTENING" >> "%OUT%" 2>&1
netstat -ano | findstr /r /c:":5060 .*LISTENING" >> "%OUT%" 2>&1

>> "%OUT%" echo.
>> "%OUT%" echo --- start on the deployed source ---
REM  --------------------------------------------------------------------
REM  CALL IT BY PATH, NOT BY NAME (2026-08-27). This is the P17 hazard
REM  arriving through a door the P17 guard does not watch.
REM
REM  `call covenant_prod.bat` relies on cmd searching the CURRENT directory,
REM  which line 20 has already made this folder. That search is switched off
REM  whenever the parent process exports NoDefaultCurrentDirectoryInExePath=1
REM  -- Git Bash does, so does anything launched from it, and so does the
REM  `python verify_deploy.py` path this project documents. Measured that
REM  day: cmd answered "'covenant_prod.bat' is not recognized as an internal
REM  or external command" with the variable set, and resolved with it clear.
REM
REM  The stop above ALWAYS succeeds. So under that parent this script stopped
REM  the nodes and then could not start them -- the exact take-it-down-and-
REM  leave-it-down outcome P17 was written to prevent, except P17 asks about
REM  the judge and this is the launcher not resolving. %~dp0 is this script's
REM  own folder and costs nothing.
REM  --------------------------------------------------------------------
REM  --------------------------------------------------------------------
REM  DO NOT REDIRECT THIS CALL INTO %OUT% (2026-08-27). It deadlocks the
REM  NEXT restart, and it does it silently.
REM
REM  covenant_prod.bat `start`s three node windows and a watchdog. Every
REM  one of them INHERITS whatever handle this line points stdout at, and
REM  holds it for as long as the node runs. Point it at NODE_RESTART.txt
REM  and the running chain owns this script's own report file.
REM
REM  Measured that day, with the nodes up from a restart 12 minutes earlier:
REM  every `>> "%OUT%"` in this file answered "The process cannot access the
REM  file because it is being used by another process", the script stopped
REM  nothing, started nothing, wrote nothing, and returned 255. A control
REM  write to any other filename in the same folder succeeded, so it was
REM  this one file and not the folder.
REM
REM  Worse than failing: verify_deploy.py printed "exit code 255" and then
REM  reported PASS, because its step 4 found the PREVIOUS restart's nodes
REM  still up and still matching disk. A restart that never happened,
REM  verified green. That half is fixed in verify_deploy.py.
REM
REM  So the launcher writes to a scratch file that nobody needs afterwards,
REM  and its contents are copied in here. The inherited handle still leaks
REM  to the nodes -- it just leaks onto something disposable. %RANDOM% twice
REM  because a single one repeats often enough to matter when two restarts
REM  land in the same second.
REM  --------------------------------------------------------------------
set "PRODLOG=%TEMP%\covenant_prod_%RANDOM%%RANDOM%.txt"
call "%~dp0covenant_prod.bat" > "%PRODLOG%" 2>&1
type "%PRODLOG%" >> "%OUT%" 2>nul

timeout /t 25 /nobreak >nul

>> "%OUT%" echo.
>> "%OUT%" echo --- AFTER: health A ---
curl -s -m 10 http://127.0.0.1:5000/health >> "%OUT%" 2>&1
>> "%OUT%" echo.
>> "%OUT%" echo --- AFTER: health B ---
curl -s -m 10 http://127.0.0.1:5020/health >> "%OUT%" 2>&1
>> "%OUT%" echo.
>> "%OUT%" echo --- AFTER: health C ---
curl -s -m 10 http://127.0.0.1:5060/health >> "%OUT%" 2>&1
>> "%OUT%" echo.
>> "%OUT%" echo ==== DONE %DATE% %TIME% ====
type "%OUT%"
echo.
pause
endlocal

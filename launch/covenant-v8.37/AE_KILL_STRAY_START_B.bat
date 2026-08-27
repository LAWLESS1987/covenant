@echo off
REM ===========================================================================
REM  AE_KILL_STRAY_START_B.bat -- 2026-08-22
REM
REM  WHY. Node B refused to start: v8.29's preflight said 127.0.0.1:5001
REM  "answered like an HTTP server, not a Covenant P2P listener". It was right.
REM  A node leaked by the test sweep (test_a1a_a2 died on Windows' unsupported
REM  SIGINT and never killed its children) was running with --port 5001, so it
REM  held 5001 as its FLASK API -- the same port node A uses for P2P. The
REM  control did exactly what A2 exists for: it refused to boot into a state
REM  where two nodes look peered and neither hears the other.
REM
REM  This kills only the stray -- identified by port 5002, which is the stray's
REM  P2P port and belongs to nothing else (node A holds 5000/5001/5011, node B
REM  would hold 5020/5021/5031) -- then starts node B.
REM ===========================================================================
setlocal
cd /d "%~dp0"
set OUT=STRAY_FIX.txt
> "%OUT%" echo ==== stray fix %DATE% %TIME% ====
>> "%OUT%" echo --- before ---
netstat -ano | findstr /r /c:":500[12] .*LISTENING" >> "%OUT%" 2>&1
>> "%OUT%" echo --- killing whatever holds 5002 (the stray's P2P) ---
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /r /c:":5002 .*LISTENING"') do taskkill /f /t /pid %%p >> "%OUT%" 2>&1
timeout /t 4 /nobreak >nul
>> "%OUT%" echo --- after: 5001 should be node A only, 5002 gone ---
netstat -ano | findstr /r /c:":500[12] .*LISTENING" >> "%OUT%" 2>&1
>> "%OUT%" echo.
>> "%OUT%" echo --- start ---
call covenant_prod.bat >> "%OUT%" 2>&1
timeout /t 25 /nobreak >nul
>> "%OUT%" echo.
>> "%OUT%" echo --- health A ---
curl -s -m 10 http://127.0.0.1:5000/health >> "%OUT%" 2>&1
>> "%OUT%" echo.
>> "%OUT%" echo --- health B ---
curl -s -m 10 http://127.0.0.1:5020/health >> "%OUT%" 2>&1
>> "%OUT%" echo.
>> "%OUT%" echo ==== DONE %DATE% %TIME% ====
type "%OUT%"
pause
endlocal

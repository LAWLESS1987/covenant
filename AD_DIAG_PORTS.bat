@echo off
REM Diagnose what is listening on the covenant port block before deciding
REM anything about the preflight refusal. Written 2026-08-22.
setlocal
cd /d "%~dp0"
set OUT=PORT_DIAG.txt
> "%OUT%" echo ==== port diag %DATE% %TIME% ====
>> "%OUT%" echo.
>> "%OUT%" echo --- everything listening in 5000-5040 ---
netstat -ano | findstr /r /c:":50[0-4][0-9] .*LISTENING" >> "%OUT%" 2>&1
>> "%OUT%" echo.
>> "%OUT%" echo --- what those PIDs are ---
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /r /c:":50[0-4][0-9] .*LISTENING"') do tasklist /fi "pid eq %%p" /v /fo list >> "%OUT%" 2>&1
>> "%OUT%" echo.
>> "%OUT%" echo --- raw probe of 5001: what does it answer to a well-formed GET ---
curl -s -m 5 -i http://127.0.0.1:5001/ >> "%OUT%" 2>&1
>> "%OUT%" echo.
>> "%OUT%" echo --- and 5002 ---
curl -s -m 5 -i http://127.0.0.1:5002/ >> "%OUT%" 2>&1
>> "%OUT%" echo.
>> "%OUT%" echo --- node A health ---
curl -s -m 8 http://127.0.0.1:5000/health >> "%OUT%" 2>&1
>> "%OUT%" echo.
>> "%OUT%" echo --- node A peers ---
curl -s -m 8 http://127.0.0.1:5000/peers >> "%OUT%" 2>&1
>> "%OUT%" echo.
>> "%OUT%" echo ==== DONE ====
type "%OUT%"
pause
endlocal

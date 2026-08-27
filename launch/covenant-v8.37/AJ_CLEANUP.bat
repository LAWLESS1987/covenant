@echo off
REM ===========================================================================
REM  AJ_CLEANUP.bat -- close the console windows today's runs left behind, and
REM  nothing else. 2026-08-22.
REM
REM  Measured: 20 cmd.exe + 26 conhost.exe + 16 OpenConsole.exe = ~540 MB
REM  across 62 processes, on a box with 2.8 GB free and a 5.2 GB judge model
REM  that has to fit in it. Every one of those windows is a launcher of mine
REM  sitting at its final `pause`.
REM
REM  Matched BY WINDOW TITLE against the launcher names only. The node windows
REM  are titled "Covenant Node A", "Covenant Node B" and "Covenant Watchdog"
REM  and are not matched -- and any console of yours that is not one of these
REM  launchers is not matched either.
REM ===========================================================================
setlocal
cd /d "%~dp0"
set OUT=CLEANUP.txt
> "%OUT%" echo ==== cleanup %DATE% %TIME% ====
>> "%OUT%" echo --- before ---
"%SystemRoot%\System32\wbem\wmic.exe" OS get FreePhysicalMemory /format:list 2>nul | findstr /r "." >> "%OUT%"

>> "%OUT%" echo.
>> "%OUT%" echo --- closing leftover launcher consoles ---
set PY=python
if exist ".venv\Scripts\python.exe" set PY=.venv\Scripts\python.exe
"%PY%" cleanup_consoles.py >> "%OUT%" 2>&1

>> "%OUT%" echo.
>> "%OUT%" echo --- removing the junk file a broken one-liner created ---
if exist "4)" del "4)" >> "%OUT%" 2>&1
if exist "4)" echo   still there, delete by hand >> "%OUT%" 2>&1

timeout /t 3 /nobreak >nul
>> "%OUT%" echo.
>> "%OUT%" echo --- after ---
"%SystemRoot%\System32\wbem\wmic.exe" OS get FreePhysicalMemory /format:list 2>nul | findstr /r "." >> "%OUT%"
>> "%OUT%" echo.
>> "%OUT%" echo --- nodes still up? ---
curl -s -m 8 http://127.0.0.1:5000/health >> "%OUT%" 2>&1
>> "%OUT%" echo.
curl -s -m 8 http://127.0.0.1:5020/health >> "%OUT%" 2>&1
>> "%OUT%" echo.
>> "%OUT%" echo ==== DONE ====
type "%OUT%"
echo.
pause
endlocal

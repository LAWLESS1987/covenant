@echo off
REM AI_TOPMEM.bat -- who is actually holding the RAM. Read-only. 2026-08-22.
REM The logic is in topmem.py, NOT inlined here: cmd expands %% inside a
REM python -c string and the first version printed nothing at all.
setlocal
cd /d "%~dp0"
set PY=python
if exist ".venv\Scripts\python.exe" set PY=.venv\Scripts\python.exe
> TOPMEM.txt echo ==== top memory %DATE% %TIME% ====
"%PY%" topmem.py >> TOPMEM.txt 2>&1
type TOPMEM.txt
echo.
pause
endlocal

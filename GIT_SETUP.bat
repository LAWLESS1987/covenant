@echo off
REM ===========================================================================
REM  GIT_SETUP.bat -- put the repository into a real, pushable state.
REM  2026-08-27.
REM
REM  It commits today's work, untracks the portfolio and the launcher reports,
REM  merges the unmerged branches into main, and regenerates the manifest.
REM  It PUSHES NOTHING -- there is no remote, and pushing is GITHUB_PUSH.bat.
REM
REM  It must run on Windows rather than over the file bridge: the bridge mount
REM  cannot delete files, and git deletes a .lock after every ref write, so
REM  over the bridge each git write poisons the next one.
REM
REM  Everything is recoverable: every branch head was tagged under
REM  refs/backup/2026-08-27/ first.
REM
REM  M28: logic in Python, GOTO labels, no parenthesised IF blocks.
REM ===========================================================================
setlocal
cd /d "%~dp0"
title COVENANT -- GIT SETUP
set PY=python
if exist ".venv\Scripts\python.exe" set PY=.venv\Scripts\python.exe

"%PY%" git_setup.py
set RC=%ERRORLEVEL%

echo.
if "%RC%"=="0" goto OK
echo   STOPPED. Read the reason above. Nothing after that point ran.
goto DONE
:OK
echo   Done. Nothing was pushed.
:DONE
echo.
pause
endlocal

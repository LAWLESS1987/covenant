@echo off
REM ===========================================================================
REM  GITHUB_PUSH.bat -- publish this repository to GitHub, as you. 2026-08-27.
REM
REM  It authenticates with YOUR credentials, through the GitHub CLI if you have
REM  it or Git Credential Manager if you don't. No token is typed into it or
REM  visible to it.
REM
REM  It REFUSES if the working tree is dirty, and it defaults to a PRIVATE
REM  repository because holdings.txt and TRADING_POLICY.json are still in the
REM  git HISTORY -- untracking them on 2026-08-27 protected every future commit
REM  and nothing about the past.
REM
REM    GITHUB_PUSH.bat                 private repo, named after this folder
REM    GITHUB_PUSH.bat --dry-run       say what it would do, do nothing
REM    GITHUB_PUSH.bat --remote <url>  push to a repo you already created
REM    GITHUB_PUSH.bat --name <name>   choose the repository name
REM
REM  Run GIT_SETUP.bat first if the tree is not clean.
REM  M28: logic in Python, GOTO labels, no parenthesised IF blocks.
REM ===========================================================================
setlocal
cd /d "%~dp0"
title COVENANT -- GITHUB PUSH
set PY=python
if exist ".venv\Scripts\python.exe" set PY=.venv\Scripts\python.exe

"%PY%" github_push.py %*
set RC=%ERRORLEVEL%

echo.
if "%RC%"=="0" goto OK
echo   Nothing was pushed. The reason is above.
goto DONE
:OK
echo   Finished.
:DONE
echo.
pause
endlocal

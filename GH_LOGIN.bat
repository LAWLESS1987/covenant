@echo off
REM ===========================================================================
REM  GH_LOGIN.bat -- log the GitHub CLI in as you, then publish. 2026-08-27.
REM
REM  gh IS installed on this machine, bundled inside Copilot Desktop, and it is
REM  NOT on PATH -- so `gh auth login` typed bare does not resolve. This finds
REM  the real binary and runs the login against it.
REM
REM  A one-time code appears and your browser opens. Paste it there and
REM  approve. THAT PART IS YOURS: the credential is issued in your name, and
REM  Claude neither types nor sees it. Everything after it is automatic --
REM  the private repository is created and pushed in the same sitting.
REM
REM  M28: logic in Python, GOTO labels, no parenthesised IF blocks.
REM ===========================================================================
setlocal
cd /d "%~dp0"
title COVENANT -- GH LOGIN
set PY=python
if exist ".venv\Scripts\python.exe" set PY=.venv\Scripts\python.exe

"%PY%" gh_login.py %*
set RC=%ERRORLEVEL%

echo.
if "%RC%"=="0" goto OK
echo   Not published. The reason is above, and in GITHUB_PUSH.txt
goto DONE
:OK
echo   Published.
:DONE
echo.
pause
endlocal

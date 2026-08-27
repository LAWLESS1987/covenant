@echo off
REM ===========================================================================
REM  GO.bat -- the one double-click for "save my work and publish it".
REM  2026-08-27.
REM
REM  It runs GIT_SETUP (commit + merge) and then GITHUB_PUSH (publish), in that
REM  order, in one window. Either step can refuse, and if the first one refuses
REM  the second is not attempted.
REM
REM  WHY IT EXISTS. The two scripts were correct separately and annoying
REM  together: the push refuses on a dirty tree, so every edit meant two
REM  double-clicks in the right order -- and every run writes a report, which
REM  re-sorts the folder, which moves the file you were about to click. A
REM  correct sequence that is easy to perform in the wrong order will be
REM  performed in the wrong order.
REM
REM  Both steps still write their own transcripts: GIT_SETUP.txt and
REM  GITHUB_PUSH.txt.
REM
REM    GO.bat                  commit, merge, publish (PRIVATE)
REM    GO.bat --dry-run        commit and merge, then say what the push WOULD do
REM
REM  M28: logic in Python, GOTO labels, no parenthesised IF blocks.
REM ===========================================================================
setlocal
cd /d "%~dp0"
title COVENANT -- GO
set PY=python
if exist ".venv\Scripts\python.exe" set PY=.venv\Scripts\python.exe

echo.
echo   ==========================================================
echo    STEP 1 of 2 -- commit and merge
echo   ==========================================================
"%PY%" git_setup.py
if errorlevel 1 goto SETUPFAILED

echo.
echo   ==========================================================
echo    STEP 2 of 2 -- publish to GitHub
echo   ==========================================================
"%PY%" github_push.py %*
set RC=%ERRORLEVEL%
echo.
if "%RC%"=="0" goto OK
echo   The push did not complete. The reason is above, and in GITHUB_PUSH.txt
goto DONE

:SETUPFAILED
echo.
echo   STEP 1 refused, so STEP 2 was NOT attempted. Read GIT_SETUP.txt
goto DONE

:OK
echo   Published.
:DONE
echo.
pause
endlocal

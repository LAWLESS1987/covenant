@echo off
REM ===========================================================================
REM  AP_CONSOLE.bat -- the operational console. 2026-08-27, for v8.37.
REM
REM  One page instead of fifteen of these files. It polls every node, shows
REM  the watchdog's pulse, and -- ONLY when you ask for it -- runs the things
REM  that are otherwise a double-click, and signs a transaction.
REM
REM  TWO MODES, AND THE DIFFERENCE IS NOT COSMETIC:
REM
REM    AP_CONSOLE.bat            READ-ONLY. It looks. It cannot touch anything.
REM    AP_CONSOLE.bat --armed    the buttons and the transaction panel work.
REM
REM  --armed sets COVENANT_APP_ACTIONS=1 for this window only. Closing the
REM  window disarms it. There is no persistent setting and no way to arm it
REM  from inside the page: a console you can arm from the thing it controls is
REM  not a control.
REM
REM  It binds 127.0.0.1 and nothing moves that. Not an argument here, not an
REM  environment variable, not a config file. If it ever needs to be on the
REM  network that is a different program with an auth story.
REM
REM  M28 throughout: GOTO labels, no parenthesised IF blocks, no bare "("
REM  outside a REM, CRLF line endings.
REM ===========================================================================
setlocal
cd /d "%~dp0"
title COVENANT CONSOLE
set PY=python
if exist ".venv\Scripts\python.exe" set PY=.venv\Scripts\python.exe
set COVENANT_APP_PORT=5199

if /I "%~1"=="--armed" goto ARMED
if /I "%~1"=="-a" goto ARMED
goto READONLY

:ARMED
set COVENANT_APP_ACTIONS=1
echo.
echo   ==========================================================
echo    COVENANT CONSOLE  --  ARMED
echo   ==========================================================
echo.
echo    The buttons work. So does the transaction panel.
echo    Arming lives in THIS WINDOW ONLY -- close it and it is gone.
echo.
goto GO

:READONLY
set COVENANT_APP_ACTIONS=
echo.
echo   ==========================================================
echo    COVENANT CONSOLE  --  read-only
echo   ==========================================================
echo.
echo    It looks. It cannot touch anything.
echo    Run  AP_CONSOLE.bat --armed  to enable the buttons.
echo.
goto GO

:GO
echo    Opening http://127.0.0.1:%COVENANT_APP_PORT%/ in your browser.
echo    Leave THIS WINDOW OPEN -- closing it stops the console.
echo.
start "" "http://127.0.0.1:%COVENANT_APP_PORT%/"
"%PY%" covenant_app.py
set RC=%ERRORLEVEL%
echo.
if "%RC%"=="1" goto PORTBUSY
if "%RC%"=="2" goto REFUSED
echo    Console stopped.
goto END

:PORTBUSY
echo    Could not bind port %COVENANT_APP_PORT%.
echo    Run AO_PORT_PICK.bat to find a free block, then set COVENANT_APP_PORT.
goto END

:REFUSED
echo    The console REFUSED TO START. Read the line above it: something has
echo    changed BIND_HOST away from 127.0.0.1, and it will not run that way.
goto END

:END
echo.
pause

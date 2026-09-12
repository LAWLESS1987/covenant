@echo off
REM ============================================================================
REM  covenant_install.bat -- make it survive a reboot.
REM
REM  A hand-started set of console windows does not come back after a restart.
REM  This registers a Scheduled Task that runs covenant_prod.bat at logon.
REM  (Until 2026-09-12 this file also persisted a local model server's settings
REM  into the user environment; that server was removed on 2026-09-07.)
REM
REM  covenant_prod.bat is idempotent -- it starts only what is not already
REM  running and never deletes a database -- so running it at every logon is
REM  safe.
REM
REM    covenant_install.bat            install
REM    covenant_install.bat uninstall  remove the task
REM ============================================================================
setlocal
cd /d "%~dp0"
set TASK=CovenantNode

if /i "%~1"=="uninstall" goto :uninstall

echo.
echo === 1/2  Scheduled Task at logon ===
schtasks /query /tn "%TASK%" >nul 2>nul
if %errorlevel% equ 0 (
  echo   task exists - replacing it.
  schtasks /delete /tn "%TASK%" /f >nul 2>nul
)
schtasks /create /tn "%TASK%" /tr "\"%~dp0covenant_prod.bat\"" /sc onlogon /rl highest /f
if %errorlevel% neq 0 (
  echo   FAILED to create the task. Run this from an Administrator prompt,
  echo   or start covenant_prod.bat by hand after each logon.
) else (
  echo   created: "%TASK%" runs covenant_prod.bat at logon.
  echo   remove it with:  covenant_install.bat uninstall
)

echo.
echo === 2/2  Verify ===
schtasks /query /tn "%TASK%" /fo list 2>nul | findstr /i "TaskName Status Next"
echo.
echo Now run:              covenant_prod.bat
echo Check any time with:  covenant_prod.bat status
pause
exit /b 0

:uninstall
echo Removing scheduled task...
schtasks /delete /tn "%TASK%" /f 2>nul
echo Done. Nodes and databases untouched - use covenant_prod.bat stop.
pause
exit /b 0

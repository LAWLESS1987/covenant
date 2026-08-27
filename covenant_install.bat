@echo off
REM ============================================================================
REM  covenant_install.bat -- make it survive a reboot.
REM
REM  Two things a hand-started pair of console windows does not do: come back
REM  after a restart, and keep its Ollama tuning. This fixes both.
REM
REM    1. setx the OLLAMA_* server settings, so the tray-started Ollama picks
REM       them up on every boot instead of only when a .bat starts the server.
REM    2. a Scheduled Task that runs covenant_prod.bat at logon.
REM
REM  covenant_prod.bat is idempotent -- it starts only what is not already
REM  running and never deletes a database -- so running it at every logon is
REM  safe.
REM
REM    covenant_install.bat            install
REM    covenant_install.bat uninstall  remove the task, clear the variables
REM ============================================================================
setlocal
cd /d "%~dp0"
set TASK=CovenantNode

if /i "%~1"=="uninstall" goto :uninstall

echo.
echo === 1/3  Persisting Ollama server settings ===
echo These need to be in your USER environment, not just a .bat, because the
echo Ollama server on Windows is started by the tray app at logon.
setx OLLAMA_HOST             "127.0.0.1:11434" >nul
setx OLLAMA_NUM_PARALLEL     "1"               >nul
setx OLLAMA_MAX_LOADED_MODELS "3"              >nul
setx OLLAMA_KEEP_ALIVE       "60m"             >nul
setx OLLAMA_FLASH_ATTENTION  "1"               >nul
setx OLLAMA_KV_CACHE_TYPE    "q8_0"            >nul
setx OLLAMA_CONTEXT_LENGTH   "2048"            >nul
echo   set. Ollama must be RESTARTED to read them ^(tray icon, Quit, reopen^).
echo   loopback only: it has no authentication, so anything that can reach
echo   the port can load models and read prompts.

echo.
echo === 2/3  Scheduled Task at logon ===
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
echo === 3/3  Verify ===
schtasks /query /tn "%TASK%" /fo list 2>nul | findstr /i "TaskName Status Next"
echo.
echo Restart Ollama now, then run:  covenant_prod.bat
echo Check any time with:           covenant_prod.bat status
pause
exit /b 0

:uninstall
echo Removing scheduled task...
schtasks /delete /tn "%TASK%" /f 2>nul
echo Clearing OLLAMA_* variables this script set...
for %%V in (OLLAMA_HOST OLLAMA_NUM_PARALLEL OLLAMA_MAX_LOADED_MODELS OLLAMA_KEEP_ALIVE OLLAMA_FLASH_ATTENTION OLLAMA_KV_CACHE_TYPE OLLAMA_CONTEXT_LENGTH) do (
  reg delete "HKCU\Environment" /v %%V /f >nul 2>nul
  echo   cleared %%V
)
echo Done. Nodes and databases untouched - use covenant_prod.bat stop.
pause
exit /b 0

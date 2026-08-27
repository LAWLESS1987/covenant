@echo off
REM ============================================================================
REM  ollama_tune.bat -- tune the Ollama SERVER on this PC for one job:
REM  short, structured, semantic verdicts from a large model on CPU.
REM
REM  Two kinds of setting exist and they are not interchangeable:
REM
REM    per-request  (num_ctx, num_predict, temperature, keep_alive)
REM                 covenant_judge_ollama.py already sends these on every
REM                 call. Nothing to do here.
REM
REM    server-side  (flash attention, KV cache type, parallel slots, bind
REM                 address) belong to the ollama.exe process, which on
REM                 Windows is started by the tray app -- NOT by this script.
REM                 They must be set with setx and Ollama restarted.
REM
REM  This script only does the second kind. It is reversible: run
REM    ollama_tune.bat undo
REM  to clear everything it set.
REM ============================================================================
setlocal EnableDelayedExpansion
cd /d "%~dp0"

if /i "%~1"=="undo" goto :undo

echo.
echo === Ollama server tuning ===
echo.
echo Current OLLAMA_* environment:
set OLLAMA 2>nul || echo   (none set)
echo.
echo This will set, for your user account:
echo.
echo   OLLAMA_HOST=127.0.0.1:11434   loopback only. Ollama has NO auth: any
echo                                 process or machine that can reach the
echo                                 port can load models and read your
echo                                 prompts. Do not bind 0.0.0.0.
echo   OLLAMA_NUM_PARALLEL=1         one judge, one slot. Parallel slots each
echo                                 get their own KV cache, so leaving this
echo                                 on auto multiplies RAM for concurrency
echo                                 you will never use.
echo   OLLAMA_MAX_LOADED_MODELS=3    one slot per DISTINCT judge model. At 1,
echo                                 every judge call evicts the previous one
echo                                 and pays a full reload: measured 23.7s
echo                                 wasted per transaction with three judges.
echo   OLLAMA_KEEP_ALIVE=30m         a 24GB model reloaded per verdict is the
echo                                 difference between seconds and minutes.
echo   OLLAMA_FLASH_ATTENTION=1      cheaper attention, less KV memory.
echo   OLLAMA_KV_CACHE_TYPE=q8_0     roughly halves KV cache RAM. Needs flash
echo                                 attention on. Negligible effect on a
echo                                 60-token JSON verdict.
echo   OLLAMA_CONTEXT_LENGTH=2048    the judge prompt is ~500 tokens. The
echo                                 4096 default allocates cache you will
echo                                 never fill.
echo.
choice /c YN /m "Apply these"
if errorlevel 2 ( echo Nothing changed. & pause & exit /b 1 )

setx OLLAMA_HOST "127.0.0.1:11434"   >nul
setx OLLAMA_NUM_PARALLEL "1"         >nul
setx OLLAMA_MAX_LOADED_MODELS "3"    >nul
setx OLLAMA_KEEP_ALIVE "30m"         >nul
setx OLLAMA_FLASH_ATTENTION "1"      >nul
setx OLLAMA_KV_CACHE_TYPE "q8_0"     >nul
setx OLLAMA_CONTEXT_LENGTH "2048"    >nul
echo   environment set.

echo.
echo === Power plan ===
echo On a laptop, CPU inference on a balanced plan runs at a fraction of
echo full speed. Switching to High performance while the node runs.
powercfg /getactivescheme
powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c >nul 2>nul
if errorlevel 1 (
  echo   High performance plan not present ^(common on modern laptops^).
  echo   Set Settings ^> System ^> Power ^> Power mode to "Best performance".
) else (
  echo   switched to High performance.
  echo   ollama_tune.bat undo puts it back to Balanced.
)

echo.
echo ============================================================
echo  RESTART OLLAMA NOW -- the server reads these at startup only.
echo    Right-click the Ollama tray icon, Quit, then start it again.
echo  Then confirm with:  ollama ps
echo ============================================================
pause
exit /b 0

:undo
echo Clearing OLLAMA_* settings this script set...
for %%V in (OLLAMA_HOST OLLAMA_NUM_PARALLEL OLLAMA_MAX_LOADED_MODELS OLLAMA_KEEP_ALIVE OLLAMA_FLASH_ATTENTION OLLAMA_KV_CACHE_TYPE OLLAMA_CONTEXT_LENGTH) do (
  reg delete "HKCU\Environment" /v %%V /f >nul 2>nul
  echo   cleared %%V
)
powercfg /setactive 381b4222-f694-41f0-9685-ff5bb260df2e >nul 2>nul
echo   power plan back to Balanced.
echo Restart Ollama for this to take effect.
pause
exit /b 0

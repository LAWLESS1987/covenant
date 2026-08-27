@echo off
REM ============================================================================
REM  covenant_efficient.bat -- lowest energy per verdict, measured not guessed.
REM
REM   1. restart Ollama with the memory-lean server settings applied
REM   2. pull qwen3:4b and qwen3:1.7b (small, fast, ~2.5GB and ~1.4GB)
REM   3. bench 1.7b / 4b / 8b on the same six cases
REM   4. report the SMALLEST model that still scores 6/6
REM
REM  The power plan is deliberately LEFT ALONE. ollama_tune.bat switches to
REM  High performance, which is the right call for speed and the wrong one if
REM  you are optimising for energy on a laptop.
REM
REM  Your two node windows keep running. A verdict arriving during the ~20s
REM  Ollama restart would fail closed and be rejected -- so do not submit a
REM  transaction while this runs.
REM
REM  Everything lands in eff_out.txt.
REM ============================================================================
setlocal EnableDelayedExpansion
cd /d "%~dp0"
set LOG=eff_out.txt
echo === covenant_efficient.bat  %DATE% %TIME% === > %LOG%

echo. & echo [1/4] Restarting Ollama with memory-lean settings
echo ---- [1/4] ollama restart ---- >> %LOG%
echo   stopping...
taskkill /f /im "ollama app.exe" >nul 2>nul
taskkill /f /im ollama.exe       >nul 2>nul
timeout /t 4 /nobreak >nul

REM These are inherited by the server process started below. Nothing is
REM written to your user environment; close this window and they are gone.
set OLLAMA_HOST=127.0.0.1:11434
set OLLAMA_NUM_PARALLEL=1
set OLLAMA_MAX_LOADED_MODELS=3
set OLLAMA_KEEP_ALIVE=30m
set OLLAMA_FLASH_ATTENTION=1
set OLLAMA_KV_CACHE_TYPE=q8_0
set OLLAMA_CONTEXT_LENGTH=2048

echo   starting with flash attention, q8_0 KV cache, 3 model slots, ctx 2048...
start "Ollama (lean)" /min cmd /c "ollama serve"
timeout /t 12 /nobreak >nul
curl -s -m 10 http://127.0.0.1:11434/api/tags >nul 2>nul
if %errorlevel% neq 0 (
  echo   FAILED - Ollama not answering after restart.
  echo   FAILED: no response after restart >> %LOG%
  goto :done
)
echo   up.
echo   restarted with lean settings >> %LOG%
echo -- bound to (blank means loopback only) -- >> %LOG%
netstat -ano | findstr ":11434" >> %LOG% 2>&1

echo. & echo [2/4] Smaller candidates
echo. >> %LOG% & echo ---- [2/4] pull ---- >> %LOG%
ollama list | findstr /c:"qwen3:4b" >nul 2>nul
if %errorlevel% neq 0 ( echo   pulling qwen3:4b ^(~2.5GB^)... & ollama pull qwen3:4b ) else ( echo   qwen3:4b present. )
ollama list | findstr /c:"qwen3:1.7b" >nul 2>nul
if %errorlevel% neq 0 ( echo   pulling qwen3:1.7b ^(~1.4GB^)... & ollama pull qwen3:1.7b ) else ( echo   qwen3:1.7b present. )
ollama list >> %LOG% 2>&1

echo. & echo [3/4] Benching 1.7b vs 4b vs 8b -- six cases each
echo. >> %LOG% & echo ---- [3/4] bench ---- >> %LOG%
if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"
python bench_models.py
type bench_models_out.txt >> %LOG% 2>&1

echo. & echo [4/4] Done
:done
echo. >> %LOG%
echo === finished %DATE% %TIME% === >> %LOG%
echo.
echo ============================================================
echo Results in eff_out.txt. Tell Claude "efficient done".
echo Nothing was switched automatically -- the summary says which
echo model to move to, and Claude will make the edit.
echo ============================================================
pause
endlocal
